"""
Log-based detector for the techniques hyperject simulates. Reads the JSONL
request log produced by the mock collector (adapt read_events() for real ingest
logs) and flags each simulated attack technique. This is the blue-team half of
the loop: anything that fires in the sim but NOT here is a coverage gap.
"""
from __future__ import annotations

import base64
import json
import re
from collections import defaultdict

from . import ui

# Tunables --------------------------------------------------------------------
BULK_THRESHOLD = 8           # events to one (client, path) at/above => flood
LARGE_BODY_BYTES = 20000     # oversized ingest payload
COVERT_FIELD_HINTS = ("app.version", "ai.application.ver", "application.ver")
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{12,}={0,2}")


def read_events(path: str):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def is_unauthenticated(ev: dict) -> bool:
    headers = {k.lower(): v for k, v in ev.get("headers", {}).items()}
    query = {k.lower(): v for k, v in ev.get("query", {}).items()}
    if "authorization" in headers:
        return False
    if query.get("client-id", [""])[0].upper() == "NO_AUTH":
        return True
    return "authorization" not in headers


#: OTLP/HTTP signal paths and the body markers of each OTLP request type
OTLP_SIGNALS = {
    "/v1/traces": "resourceSpans",
    "/v1/metrics": "resourceMetrics",
    "/v1/logs": "resourceLogs",
}
#: Foundry continuous-evaluation results land as this message value
GENAI_EVAL_MARKER = "gen_ai.evaluation.result"


def find_otlp_signal(ev: dict):
    """Return the OTLP signal ('traces'/'metrics'/'logs') if this looks like an
    OTLP/HTTP export, else None. Matches on path or on the OTLP body marker
    (JSON), so it fires for both JSON and protobuf exports."""
    path = ev.get("path", "") or ""
    body = ev.get("body", "") or ""
    for sig_path, marker in OTLP_SIGNALS.items():
        if path.endswith(sig_path) or marker in body:
            return sig_path.rsplit("/", 1)[-1]
    return None


def otlp_encoding(ev: dict) -> str:
    """Best-effort OTLP wire encoding of an event, from its Content-Type header."""
    ctype = ""
    for k, v in (ev.get("headers", {}) or {}).items():
        if k.lower() == "content-type":
            ctype = (v or "").lower()
            break
    return "protobuf" if "x-protobuf" in ctype else "json"


def is_quickpulse(ev: dict) -> bool:
    """Detect an Azure Monitor Live Metrics / QuickPulse ingest request."""
    path = ev.get("path", "") or ""
    if "/QuickPulseService.svc/" in path:
        return True
    return any(k.lower().startswith("x-ms-qps-")
               for k in (ev.get("headers", {}) or {}))


#: additional protobuf telemetry ingest surfaces, keyed by request path suffix
OTHER_INGEST = {
    "/api/v1/write": ("REMOTE_WRITE_INGEST", "Prometheus remote-write accepted"),
    "/loki/api/v1/push": ("LOKI_INGEST", "Grafana Loki push accepted"),
    "/api/v2/spans": ("ZIPKIN_INGEST", "Zipkin spans accepted"),
}


def find_other_ingest(ev: dict):
    """Return (finding_type, detail) for Prometheus/Loki/Zipkin ingest, else None."""
    path = ev.get("path", "") or ""
    for suffix, finding in OTHER_INGEST.items():
        if path.endswith(suffix):
            return finding
    return None


def is_genai_eval_poison(ev: dict) -> bool:
    """Detect a forged agent-evaluation result (Foundry continuous evaluation
    writes gen_ai.evaluation.result with gen_ai.* attributes to App Insights)."""
    body = ev.get("body", "") or ""
    return GENAI_EVAL_MARKER in body and "gen_ai." in body


def find_covert_field(ev: dict):
    body = ev.get("body", "") or ""
    try:
        flat = json.dumps(json.loads(body))
    except Exception:
        flat = ""
    for hint in COVERT_FIELD_HINTS:
        if hint in flat or hint in body:
            for m in BASE64_RE.findall(body):
                try:
                    dec = base64.b64decode(m + "=" * (-len(m) % 4)).decode("utf-8", "ignore")
                    if dec.isprintable() and len(dec) >= 3:
                        return f"{hint} -> b64('{dec}')"
                except Exception:
                    continue
            return hint
    return None


def detect(path: str) -> int:
    findings = []
    per_client_times = defaultdict(list)

    try:
        events = list(read_events(path))
    except FileNotFoundError:
        print(f"[-] Log not found: {path}")
        print("[*] Run the mock collector and a simulation first.")
        return 0

    for ev in events:
        target = ev.get("path", "?")
        client = ev.get("client", "?")
        if is_unauthenticated(ev):
            findings.append(("UNAUTH_INGEST", client, target,
                             "telemetry accepted without Authorization header"))
        if ev.get("body_len", 0) >= LARGE_BODY_BYTES:
            findings.append(("OVERSIZED_PAYLOAD", client, target, f"{ev['body_len']} bytes"))
        covert = find_covert_field(ev)
        if covert:
            findings.append(("COVERT_FIELD_C2", client, target, f"data hidden in {covert}"))
        signal = find_otlp_signal(ev)
        if signal:
            findings.append(("OTLP_INGEST", client, target,
                             f"OpenTelemetry {signal} export accepted "
                             f"({otlp_encoding(ev)})"))
        if is_quickpulse(ev):
            findings.append(("QUICKPULSE_INGEST", client, target,
                             "Live Metrics / QuickPulse stream accepted"))
        other = find_other_ingest(ev)
        if other:
            findings.append((other[0], client, target, other[1]))
        if is_genai_eval_poison(ev):
            findings.append(("GENAI_EVAL_POISON", client, target,
                             "forged gen_ai.evaluation.result (agent-eval poisoning)"))
        per_client_times[(client, target)].append(ev.get("ts", ""))

    for (client, target), times in per_client_times.items():
        if len(times) >= BULK_THRESHOLD:
            findings.append(("BULK_FLOOD", client, target,
                             f"{len(times)} events to same endpoint"))

    rule = ui.grey("=" * 70)
    print(rule)
    print("  " + ui.bold(f"DETECTION REPORT — {len(events)} events from {path}"))
    print(rule)
    if not findings:
        print(ui.yellow("[-] No techniques detected. "
                        "If the sim ran, this is a COVERAGE GAP."))
        return 0

    by_type = defaultdict(list)
    for f in findings:
        by_type[f[0]].append(f)
    for tech, items in sorted(by_type.items()):
        print(f"\n{ui.green('[+]')} {ui.bold(tech)}  {ui.grey(f'({len(items)} hits)')}")
        for _, client, target, detail in items[:20]:
            print(f"      {ui.cyan(client)}  {target}  {ui.grey('—')} {detail}")
        if len(items) > 20:
            print(ui.grey(f"      ... and {len(items) - 20} more"))
    print()
    return len(findings)
