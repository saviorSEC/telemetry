"""
Shared infrastructure for hyperject — HTTP engine, config handling, and payload
helpers used by target modules. Target-specific logic lives in the `modules/`
package (one file per target); this file knows nothing about individual targets.

DESIGN GUARANTEES (do not remove):
  * There are NO built-in target hostnames or credentials. Every target and key
    is read from a config the operator supplies.
  * The tool refuses to run against unfilled placeholders (REPLACE_..., etc.).
  * dry-run generates and prints payloads WITHOUT sending anything.
"""
from __future__ import annotations

import base64
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import urlparse, urlunparse

from . import ui
from .transcript import Exchange
from .mwbase import RequestContext

try:
    import requests
except ImportError:  # pragma: no cover
    print("[!] The 'requests' package is required:  pip install requests", file=sys.stderr)
    raise

PLACEHOLDER_MARKERS = ("REPLACE_", "REPLACE_ME", "CHANGEME", "YOUR_")
VARIANTS = ("basic", "bulk", "large", "covert")

_VERBOSITY = 1  # 0=quiet, 1=normal, 2=verbose


def set_verbosity(level: int) -> None:
    global _VERBOSITY
    _VERBOSITY = level


# --------------------------------------------------------------------------- #
# Print helpers
# --------------------------------------------------------------------------- #

def now_iso(short: bool = False) -> str:
    fmt = "%Y-%m-%dT%H:%M:%SZ" if short else "%Y-%m-%dT%H:%M:%S.%f"
    s = datetime.now(timezone.utc).strftime(fmt)
    return s if short else s[:-3] + "Z"


def looks_like_placeholder(value: str) -> bool:
    v = str(value).upper()
    return any(m in v for m in PLACEHOLDER_MARKERS)


def info(msg: str) -> None:
    if _VERBOSITY >= 1:
        print(f"{ui.cyan('[*]')} {msg}")


def ok(msg: str) -> None:
    if _VERBOSITY >= 1:
        print(f"{ui.green('[+]')} {msg}")


def fail(msg: str) -> None:
    print(f"{ui.red('[-]')} {msg}", file=sys.stderr)


def debug(msg: str) -> None:
    if _VERBOSITY >= 2:
        print(ui.grey(f"    {msg}"))


def header(msg: str) -> None:
    if _VERBOSITY >= 1:
        rule = ui.grey("=" * 70)
        print("\n" + rule)
        print("  " + ui.bold(msg))
        print(rule)


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #

#: statuses that mean "the endpoint required authentication" (the secure outcome)
AUTH_STATUSES = (401, 403)


@dataclass
class SimResult:
    module: str
    technique: str
    target: str
    sent: int = 0
    accepted: int = 0        # endpoint took the telemetry (accept predicate matched)
    auth_required: int = 0   # endpoint answered 401/403 (rejected — secure)
    rejected: int = 0        # other non-accepting status (4xx/5xx/unexpected)
    errors: int = 0
    status_codes: list = field(default_factory=list)
    accepted_all: bool = False

    @property
    def verdict(self) -> str:
        if self.sent == 0:
            return "no-data"
        if self.accepted > 0:
            return "EXPOSED"          # accepted injected telemetry
        if self.auth_required > 0:
            return "auth-required"    # endpoint required auth (secure)
        return "rejected"


@dataclass
class Prepared:
    """A single ready-to-send request plus its acceptance predicate."""
    method: str
    url: str
    kwargs: dict
    accept: Callable


# --------------------------------------------------------------------------- #
# HTTP engine
# --------------------------------------------------------------------------- #

class Engine:
    def __init__(self, timeout: float, rate_delay: float, dry_run: bool,
                 transcript=None, middlewares=None, proxies=None, verify: bool = True,
                 max_attempts: int = 4):
        self.timeout = timeout
        self.rate_delay = rate_delay
        self.dry_run = dry_run
        #: a transcript.Transcript to record exchanges into, or None
        self.transcript = transcript
        # priority order: lower runs earlier in before_request (stable within tier)
        self.middlewares = sorted(list(middlewares or []),
                                  key=lambda m: getattr(m, "priority", 100))
        self.proxies = proxies              # {"http": ..., "https": ...} or None
        self.verify = verify                # TLS verification (False with --insecure)
        self.max_attempts = max(1, max_attempts)

    @staticmethod
    def _snapshot(req: dict) -> dict:
        body = req.get("json")
        if body is None:
            body = req.get("data")
        return {"method": req["method"], "url": req["url"],
                "params": req.get("params"), "headers": dict(req.get("headers") or {}),
                "body": body}

    def _record(self, rc) -> None:
        if self.transcript is None:
            return
        reqd = self._snapshot(rc.request)
        if rc.error is not None and rc.response is None:
            self.transcript.add(Exchange(rc.module, rc.technique, reqd, {}, error=str(rc.error)))
            return
        r = rc.response
        try:
            body = (getattr(r, "text", "") or "")[:4000]
        except Exception:
            body = ""
        self.transcript.add(Exchange(rc.module, rc.technique, reqd, {
            "status": getattr(r, "status_code", None),
            "headers": dict(getattr(r, "headers", {}) or {}),
            "body": body, "elapsed_ms": rc.elapsed_ms, "attempts": rc.attempt}))

    def _chain(self, hook: str, rc, reverse: bool = False) -> None:
        order = reversed(self.middlewares) if reverse else self.middlewares
        for mw in order:
            if not mw.applies_to(rc):
                continue
            getattr(mw, hook)(rc)
            if hook == "before_request" and rc.action == rc.SHORT_CIRCUIT:
                break

    def send(self, method: str, url: str, ctx=None, **kwargs):
        rc = RequestContext(
            request={"method": method, "url": url,
                     "headers": dict(kwargs.get("headers") or {}),
                     "params": kwargs.get("params"), "json": kwargs.get("json"),
                     "data": kwargs.get("data"),
                     "allow_redirects": kwargs.get("allow_redirects", True)},
            meta=ctx or {})

        self._chain("before_request", rc)

        if self.dry_run:
            req = rc.request
            print(ui.grey(f"    [dry-run] {req['method']} {req['url']}"))
            if req.get("params"):
                print(ui.grey(f"              params: {json.dumps(req['params'])[:300]}"))
            body = req.get("json") or req.get("data") or {}
            if isinstance(body, (bytes, bytearray)):
                shown = f"<{len(body)} bytes protobuf> {bytes(body[:32]).hex()}..."
            else:
                shown = json.dumps(body, default=str)[:300]
            print(ui.grey(f"              body:   {shown}"))
            rc.error = "dry-run"
            self._record(rc)
            return None

        # short-circuited before any network I/O
        if rc.action == rc.SHORT_CIRCUIT:
            rc.attempt = 0
            rc.clear_action()
            self._chain("after_response", rc, reverse=True)   # observers still see it
            self._record(rc)
            return rc.response

        while True:
            rc.attempt += 1
            rc.clear_action()
            req = rc.request
            if self.rate_delay:
                time.sleep(self.rate_delay)
            start = time.perf_counter()
            try:
                rc.response = requests.request(
                    req["method"], req["url"], headers=req["headers"] or None,
                    params=req["params"], json=req["json"], data=req["data"],
                    allow_redirects=req["allow_redirects"], timeout=self.timeout,
                    proxies=self.proxies, verify=self.verify)
                rc.error = None
                rc.elapsed_ms = int((time.perf_counter() - start) * 1000)
            except Exception as e:
                rc.response = None
                rc.error = e
                self._chain("on_error", rc, reverse=True)
                if rc.action == rc.RETRY and rc.attempt < self.max_attempts:
                    continue
                if rc.response is None:          # unrecovered
                    self._record(rc)
                    raise rc.error
                # recovered by middleware: fall through to after_response

            self._chain("after_response", rc, reverse=True)
            if rc.action == rc.RETRY and rc.attempt < self.max_attempts:
                continue
            break

        self._record(rc)
        return rc.response


def execute(engine: Engine, module: str, technique: str, target: str,
            preps, concurrency: int) -> SimResult:
    """Send a batch of prepared requests (optionally concurrently) and tally."""
    res = SimResult(module, technique, target)
    ctx = {"module": module, "technique": technique}

    def one(p: Prepared):
        try:
            r = engine.send(p.method, p.url, ctx=ctx, **p.kwargs)
            if r is None:                                   # dry-run
                return ("dry", None)
            code = r.status_code
            snippet = (getattr(r, "text", "") or "").replace("\n", " ")[:120]
            colored = ui.green(str(code)) if code and code < 400 else ui.red(str(code))
            debug(f"{p.method} {p.url} -> {colored}  {snippet!r}")
            if code in AUTH_STATUSES:                       # 401/403 => auth required
                return ("auth", code)
            if p.accept(r):
                return ("accept", code)
            return ("reject", code)
        except Exception as e:
            debug(f"error: {e}")
            return ("error", None)

    if concurrency > 1 and not engine.dry_run:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            outcomes = list(pool.map(one, preps))
    else:
        outcomes = [one(p) for p in preps]

    for kind, code in outcomes:
        if kind == "error":
            res.errors += 1
            continue
        if kind == "dry":
            res.sent += 1
            continue
        res.sent += 1
        if code is not None:
            res.status_codes.append(code)
        if kind == "accept":
            res.accepted += 1
        elif kind == "auth":
            res.auth_required += 1
        else:
            res.rejected += 1
    res.accepted_all = res.sent > 0 and res.accepted == res.sent
    return res


# --------------------------------------------------------------------------- #
# Config load / override / validation
# --------------------------------------------------------------------------- #

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        fail(f"Config not found: {path}")
        info("Run 'hyperject init' to scaffold one.")
        sys.exit(2)
    with open(path) as f:
        return json.load(f)


def apply_target_override(cfg: dict, base: str) -> None:
    """Rewrite every module endpoint to point at `base`, preserving each path."""
    b = urlparse(base)
    if not b.scheme or not b.netloc:
        fail(f"--target-base must be like http://127.0.0.1:8080  (got: {base})")
        sys.exit(2)

    def rewrite(u: str) -> str:
        p = urlparse(u)
        return urlunparse((b.scheme, b.netloc, p.path, p.params, p.query, p.fragment))

    for m in cfg.get("modules", {}).values():
        if m.get("base_url"):
            m["base_url"] = rewrite(m["base_url"])
        if m.get("endpoint"):
            m["endpoint"] = rewrite(m["endpoint"])
        if m.get("endpoints"):
            m["endpoints"] = [rewrite(e) for e in m["endpoints"]]


def collect_target_strings(cfg: dict) -> list:
    out = []
    for m in cfg.get("modules", {}).values():
        if not m.get("enabled", True):
            continue
        for k in ("base_url", "endpoint"):
            if m.get(k):
                out.append(m[k])
        for ep in m.get("endpoints", []) or []:
            out.append(ep)
        for ik in m.get("ikeys", []) or []:
            # a key may be a bare string or an annotated {"ikey"/"value", "label"}
            out.append(ik.get("ikey") or ik.get("value", "") if isinstance(ik, dict) else ik)
        for kd in m.get("keys", []) or []:
            out.append(kd.get("key", ""))
            out.append(kd.get("ikey", ""))
        # Azure Monitor connection strings carry their own ikey + ingestion
        # endpoint; surface the ikey so the placeholder guard still covers it.
        for cs in m.get("connection_strings", []) or []:
            raw = cs.get("value", "") if isinstance(cs, dict) else cs
            out.append(parse_connection_string(raw).get("InstrumentationKey", ""))
    return [x for x in out if x]


# --------------------------------------------------------------------------- #
# Azure Monitor connection strings (App Insights / OpenTelemetry exporter)
# --------------------------------------------------------------------------- #

#: default global telemetry ingestion endpoint when a connection string gives
#: neither an explicit IngestionEndpoint nor an EndpointSuffix.
DEFAULT_INGESTION_ENDPOINT = "https://dc.services.visualstudio.com"


def parse_connection_string(cs: str) -> dict:
    """Parse an Azure Monitor connection string (``key=value;key=value``) into a
    dict. Unknown/auto keys are preserved; whitespace is trimmed. This is the
    same string the Azure Monitor OpenTelemetry exporter is configured with."""
    parts: dict = {}
    for seg in str(cs).split(";"):
        seg = seg.strip()
        if not seg or "=" not in seg:
            continue
        k, _, v = seg.partition("=")
        parts[k.strip()] = v.strip()
    return parts


def ingestion_endpoint(parts: dict) -> str:
    """Resolve the telemetry ingestion base URL from parsed connection-string
    parts. An explicit ``IngestionEndpoint`` wins; otherwise it is derived from
    ``EndpointSuffix`` as ``dc.<suffix>`` (the ingestion prefix is ``dc``);
    otherwise the global default is used."""
    explicit = parts.get("IngestionEndpoint")
    if explicit:
        return explicit.rstrip("/")
    suffix = parts.get("EndpointSuffix")
    if suffix:
        return f"https://dc.{suffix.lstrip('.')}"
    return DEFAULT_INGESTION_ENDPOINT


def connection_string_target(cs: str) -> tuple:
    """Return ``(ikey, track_url)`` for an Azure Monitor connection string, where
    ``track_url`` is the ``/v2.1/track`` Breeze ingestion URL the SDK POSTs to."""
    parts = parse_connection_string(cs)
    ikey = parts.get("InstrumentationKey", "")
    return ikey, f"{ingestion_endpoint(parts)}/v2.1/track"


#: default Live Metrics (QuickPulse) endpoint when a connection string omits it
DEFAULT_LIVE_ENDPOINT = "https://rt.services.visualstudio.com"


def live_endpoint(parts: dict) -> str:
    """Resolve the Live Metrics (QuickPulse) base URL from parsed connection-string
    parts. Explicit ``LiveEndpoint`` wins; otherwise derived as ``live.<suffix>``."""
    explicit = parts.get("LiveEndpoint")
    if explicit:
        return explicit.rstrip("/")
    suffix = parts.get("EndpointSuffix")
    if suffix:
        return f"https://live.{suffix.lstrip('.')}"
    return DEFAULT_LIVE_ENDPOINT


def connection_string_live_target(cs: str) -> tuple:
    """Return ``(ikey, live_base_url)`` for an Azure Monitor connection string.
    QuickPulse requests go to ``{live_base}/QuickPulseService.svc/{ping,post}``."""
    parts = parse_connection_string(cs)
    return parts.get("InstrumentationKey", ""), live_endpoint(parts)


def validate_config(cfg: dict, known_modules=None) -> list:
    """Return a list of problems (empty == valid). `known_modules` is the set of
    registered module names; unknown enabled modules are flagged when provided."""
    problems = []
    targets = collect_target_strings(cfg)
    if not targets:
        problems.append("No enabled modules with targets found.")
    for t in targets:
        if looks_like_placeholder(t):
            problems.append(f"Unfilled placeholder value: {t}")
    if known_modules is not None:
        for name, m in cfg.get("modules", {}).items():
            if m.get("enabled", True) and name not in known_modules:
                problems.append(f"Unknown module '{name}' (no registered runner).")
    return sorted(set(problems))


# --------------------------------------------------------------------------- #
# Payload helpers shared by target modules
# --------------------------------------------------------------------------- #

def covert_marker(cfg: dict) -> str:
    c = cfg.get("techniques", {}).get("covert_field", {})
    return base64.b64encode(c.get("marker", "SIMULATED_C2_MARKER").encode()).decode()


def large_blob(cfg: dict) -> str:
    n = cfg.get("techniques", {}).get("large_payload_bytes", 50000)
    return base64.b64encode(os.urandom(n)).decode("ascii")


def rand_hex_id() -> str:
    return hex(random.getrandbits(64))[2:].zfill(16).upper()


def sample_hex(n: int) -> str:
    return "".join(random.choice("0123456789abcdef") for _ in range(n))


def variant_count(variant: str, cfg: dict) -> int:
    """basic/large/covert = 1 request; bulk = run.count requests (flood sim)."""
    return cfg.get("run", {}).get("count", 10) if variant == "bulk" else 1


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

_VERDICT_STYLE = {"EXPOSED": ("red",), "auth-required": ("green",),
                  "rejected": ("yellow",), "no-data": ("grey",)}


def print_results_table(results) -> None:
    if _VERBOSITY < 1:
        return
    print(f"\n{'module':15} {'technique':9} {'sent':>4} {'acc':>4} {'auth':>4} "
          f"{'rej':>4} {'err':>4}  {'verdict':13} target")
    print("-" * 92)
    for r in results:
        verdict = ui.paint(f"{r.verdict:13}", *_VERDICT_STYLE.get(r.verdict, ()))
        print(f"{r.module:15} {r.technique:9} {r.sent:>4} {r.accepted:>4} "
              f"{r.auth_required:>4} {r.rejected:>4} {r.errors:>4}  {verdict} {r.target}")
