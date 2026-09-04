"""
Command-line interface for hyperject.

Subcommands:
  run       generate injection traffic against configured targets
  list      list available modules and techniques
  init      scaffold a ready-to-run config.json (mock-collector targets)
  validate  check a config file without sending anything
  mock      run the local mock collector (safe target)
  detect    run the log detector over collected ingest logs

Targets are provided by plugin modules discovered at runtime (see registry.py).
Point targets at the mock collector or an authorized lab range only.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import asdict

from . import __version__
from . import collector
from . import detector
from . import ui
from .transcript import Transcript, Exchange, FORMATS
from .registry import discover, discover_middleware
from .core import (VARIANTS, Engine, execute, load_config, apply_target_override,
                   validate_config, print_results_table, header, info, ok, fail,
                   set_verbosity)


# --------------------------------------------------------------------------- #
# run
# --------------------------------------------------------------------------- #

def _one_pass(engine, cfg, registry, modules_filter, variants, concurrency):
    results = []
    for name, mcfg in cfg.get("modules", {}).items():
        if not mcfg.get("enabled", True):
            continue
        if modules_filter and name not in modules_filter:
            continue
        module = registry.get(name)
        if module is None:
            fail(f"Unknown module '{name}' (no registered runner) — skipping.")
            continue
        wanted = module.techniques_for(variants)
        if not wanted:
            continue
        header(f"MODULE: {name}  ({mcfg.get('description', module.description)})")
        for technique, target, preps in module.plan(mcfg, cfg, wanted):
            res = execute(engine, name, technique, target, preps, concurrency)
            tag = "ACCEPTED" if res.accepted_all else f"{res.accepted}/{res.sent}"
            (ok if res.accepted_all else info)(
                f"{technique:8} -> {target}  [{tag}]  errors={res.errors}")
            results.append(res)
    return results


def cmd_run(args) -> int:
    set_verbosity(0 if args.quiet else (2 if args.verbose else 1))
    registry = discover()
    cfg = load_config(args.config)

    if args.target_base:
        apply_target_override(cfg, args.target_base)

    run_cfg = cfg.setdefault("run", {})
    if args.count is not None:
        run_cfg["count"] = args.count
    if args.timeout is not None:
        run_cfg["timeout"] = args.timeout
    if args.delay is not None:
        run_cfg["rate_limit_delay"] = args.delay
    if args.output:
        run_cfg["output"] = args.output

    if args.seed is not None:
        random.seed(args.seed)
        info(f"Random seed fixed at {args.seed} (reproducible payloads).")

    if not args.dry_run:
        problems = validate_config(cfg, known_modules=set(registry))
        if problems:
            fail("Config invalid:")
            for p in problems:
                print(f"      {p}", file=sys.stderr)
            info("Fix these, or use --dry-run to preview without sending.")
            return 2
    else:
        info("DRY RUN — no requests will be sent.")

    # middleware chain (auto-discovered plugins, enabled per-config)
    mw_registry = discover_middleware()
    middlewares = []
    for spec in cfg.get("middleware", []):
        name = spec.get("name")
        cls = mw_registry.get(name)
        if cls is None:
            fail(f"Unknown middleware '{name}' — skipping (see 'hyperject list').")
            continue
        middlewares.append(cls(**spec.get("options", {})))
    if middlewares:
        info("Middleware: " + ", ".join(m.name for m in middlewares))

    # proxy / TLS
    proxy = args.proxy or run_cfg.get("proxy")
    proxies = {"http": proxy, "https": proxy} if proxy else None
    verify = not args.insecure
    if proxy:
        info(f"Proxying through {proxy}  (TLS verify: {verify})")
    if args.insecure:
        try:
            import urllib3
            urllib3.disable_warnings()
        except Exception:
            pass

    # transcript (full request/response review + export)
    want_transcript = bool(args.transcript or args.save_responses)
    tr = Transcript(redact=cfg.get("transcript", {}).get("redact")) if want_transcript else None

    max_attempts = args.max_attempts if args.max_attempts is not None \
        else run_cfg.get("max_attempts", 4)
    concurrency = max(1, args.concurrency)
    engine = Engine(timeout=run_cfg.get("timeout", 10),
                    rate_delay=run_cfg.get("rate_limit_delay", 0.2),
                    dry_run=args.dry_run, transcript=tr, middlewares=middlewares,
                    proxies=proxies, verify=verify, max_attempts=max_attempts)
    variants = tuple(args.techniques) if args.techniques else VARIANTS

    aggregate = []
    passes = max(1, args.repeat)
    for n in range(passes):
        header(f"hyperject BAS run — pass {n + 1}/{passes}"
               f"   techniques: {', '.join(variants)}   concurrency: {concurrency}")
        aggregate.extend(_one_pass(engine, cfg, registry, args.modules_filter,
                                   variants, concurrency))
        if n + 1 < passes:
            info(f"Sleeping {args.interval}s before next pass...")
            time.sleep(args.interval)

    header("SUMMARY")
    total_sent = sum(r.sent for r in aggregate)
    total_acc = sum(r.accepted for r in aggregate)
    total_auth = sum(r.auth_required for r in aggregate)
    total_rej = sum(r.rejected for r in aggregate)
    total_err = sum(r.errors for r in aggregate)
    if args.format == "table":
        print_results_table(aggregate)
    info(f"Passes: {passes}   techniques exercised: {len(aggregate)}")
    info(f"Requests sent: {total_sent}   accepted: {total_acc}   "
         f"auth-required: {total_auth}   rejected: {total_rej}   errors: {total_err}")

    # endpoint-exposure verdict (the recon question the source scripts answer)
    exposed = sorted({r.target for r in aggregate if r.verdict == "EXPOSED"})
    secured = sorted({r.target for r in aggregate
                      if r.verdict == "auth-required" and r.target not in exposed})
    if exposed:
        fail(f"EXPOSED — {len(exposed)} endpoint(s) accepted injected telemetry "
             "with no required auth:")
        for t in exposed:
            print("      " + ui.red(t))
    if secured:
        ok(f"Auth required (secure) on {len(secured)} endpoint(s): "
           + ", ".join(secured))
    if not exposed and not secured and not args.dry_run:
        info("No endpoint accepted or challenged with auth — check connectivity/config.")

    # full request/response transcript export (works in dry-run too)
    if args.transcript and tr is not None:
        tr.save(args.transcript, args.export)
        ok(f"Wrote {len(tr)} request/response exchanges to {args.transcript} "
           f"({args.export})")

    if not args.dry_run:
        out_path = run_cfg.get("output", "results.json")
        with open(out_path, "w") as f:
            json.dump([asdict(r) for r in aggregate], f, indent=2)
        ok(f"Per-technique acceptance summary written to {out_path}")

        if args.save_responses and tr is not None:
            with open(args.save_responses, "w") as f:
                json.dump(tr.responses_only(), f, indent=2)
            ok(f"Recorded {len(tr)} raw endpoint responses to {args.save_responses}")
            info("Review that file to see exactly what each endpoint returned / "
                 "accepted for the telemetry you sent.")
        info("Review options: 'hyperject export <file>' to beautify/convert, or "
             "'hyperject detect <ingest-log>' to see what the endpoint ingested.")

    if args.require_accept and not all(r.accepted_all for r in aggregate):
        fail("--require-accept: not every technique was accepted (see summary).")
        return 1
    return 0


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #

def cmd_list(args) -> int:
    registry = discover()
    show_all = not (args.modules_only or args.techniques_only or args.middleware_only)
    if args.techniques_only or show_all:
        print(ui.bold("Techniques:"))
        descriptions = {
            "basic": "single well-formed event",
            "bulk": "N events (run.count) — flood / volume simulation",
            "large": "oversized payload (techniques.large_payload_bytes)",
            "covert": "data hidden in a telemetry field (covert-channel/C2 sim)",
        }
        for v in VARIANTS:
            print(f"  {ui.yellow(f'{v:8}')} - {descriptions[v]}")
    if args.modules_only or show_all:
        print("\n" + ui.bold("Modules (discovered target plugins):"))
        for name, mod in registry.items():
            techs = ",".join(mod.supported_techniques)
            print(f"  {ui.cyan(f'{name:16}')} {mod.description:40} {ui.grey(f'[{techs}]')}")
    if args.middleware_only or show_all:
        print("\n" + ui.bold("Middleware (discovered request/response plugins):"))
        for name, cls in discover_middleware().items():
            print(f"  {ui.cyan(f'{name:16}')} {getattr(cls, 'description', '')}")
    return 0


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #

def cmd_init(args) -> int:
    if os.path.exists(args.output) and not args.force:
        fail(f"{args.output} already exists (use --force to overwrite).")
        return 2
    registry = discover()
    base = args.target_base.rstrip("/")
    cfg = {
        "_comment": "Generated by 'hyperject init'. Targets point at a local mock "
                    "collector. Change targets/keys to your own authorized lab before "
                    "pointing anywhere else.",
        "run": {"count": 10, "timeout": 10, "rate_limit_delay": 0.2, "output": "results.json",
                "proxy": None},
        "modules": {name: mod.default_config(base) for name, mod in registry.items()},
        "techniques": {"large_payload_bytes": 50000,
                       "covert_field": {"enabled": True, "field": "app.version",
                                        "marker": "SIMULATED_C2_MARKER"}},
        # Enable request/response middleware here, e.g.:
        #   {"name": "extra_headers", "options": {"headers": {"Authorization": "Bearer X"}}}
        "middleware": [],
        # Keys to mask in exported transcripts (case-insensitive).
        "transcript": {"redact": ["security_token", "apikey", "authorization"]},
    }
    with open(args.output, "w") as f:
        json.dump(cfg, f, indent=2)
    ok(f"Wrote {args.output} with {len(cfg['modules'])} modules (targets -> {base})")
    info("Start the target:  hyperject mock --port 8080")
    info(f"Then run:          hyperject run -c {args.output}")
    return 0


# --------------------------------------------------------------------------- #
# validate
# --------------------------------------------------------------------------- #

def cmd_validate(args) -> int:
    registry = discover()
    cfg = load_config(args.config)
    problems = validate_config(cfg, known_modules=set(registry))
    if problems:
        fail(f"{args.config} is INVALID:")
        for p in problems:
            print(f"      {p}", file=sys.stderr)
        return 1
    ok(f"{args.config} is valid. Enabled modules:")
    for name, m in cfg.get("modules", {}).items():
        if m.get("enabled", True):
            print(f"      {name}")
    return 0


# --------------------------------------------------------------------------- #
# mock / detect
# --------------------------------------------------------------------------- #

def cmd_mock(args) -> int:
    collector.serve(host=args.host, port=args.port, log_path=args.log)
    return 0


def cmd_detect(args) -> int:
    detector.detect(args.log)
    return 0


# --------------------------------------------------------------------------- #
# capture (show real OTLP request/response; optional SDK fidelity diff)
# --------------------------------------------------------------------------- #

def cmd_capture(args) -> int:
    from . import capture
    return capture.run(source=args.source, signal=args.signal,
                       encoding=args.encoding, target=args.target,
                       proxy=args.proxy, insecure=args.insecure,
                       service_name=args.service_name, diff=args.diff)


# --------------------------------------------------------------------------- #
# export (beautify / convert request-response transcripts and any JSON)
# --------------------------------------------------------------------------- #

def _load_records(path: str):
    with open(path) as f:
        text = f.read().strip()
    if not text:
        return []
    try:
        return json.loads(text)                       # JSON array/object
    except json.JSONDecodeError:
        return [json.loads(ln) for ln in text.splitlines() if ln.strip()]  # JSONL


def cmd_export(args) -> int:
    try:
        data = _load_records(args.file)
    except FileNotFoundError:
        fail(f"File not found: {args.file}")
        return 2
    except json.JSONDecodeError as e:
        fail(f"Could not parse {args.file} as JSON/JSONL: {e}")
        return 1

    fmt = args.format
    # 'pretty'/'json'/'jsonl' beautify ANY JSON; har/pretty-transcript need exchanges.
    if fmt == "pretty" and not (isinstance(data, list) and data
                                and isinstance(data[0], dict) and "request" in data[0]):
        rendered = ui.pretty_json(data)               # generic beautify (results, config, ...)
    else:
        tr = Transcript()
        for d in (data if isinstance(data, list) else [data]):
            if isinstance(d, dict) and "request" in d:
                tr.add(Exchange(d.get("module", ""), d.get("technique", ""),
                                d.get("request", {}), d.get("response", {}), d.get("error", "")))
        if len(tr) == 0:
            if fmt in ("har",):
                fail(f"{args.file} is not a transcript (no request/response records).")
                return 1
            rendered = ui.pretty_json(data)
        else:
            rendered = tr.render(fmt)

    if args.output:
        with open(args.output, "w") as f:
            f.write(rendered if rendered.endswith("\n") else rendered + "\n")
        ok(f"Wrote {args.output} ({fmt})")
    else:
        print(rendered)
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

RawFmt = argparse.RawDescriptionHelpFormatter

TOP_EPILOG = """\
workflow — send telemetry, then review what the endpoint did with it:

  1. hyperject mock                 start a safe local endpoint that logs ingest
                                    (or point at an endpoint you are authorized to check)
  2. hyperject init                 scaffold config.json from the discovered modules
  3. hyperject run                  send the telemetry; --save-responses to keep what
                                    each endpoint returned, -v to watch it live
  4. hyperject detect               review the endpoint's ingest log — which techniques
                                    it accepted, and what leaked through

Three ways to review the telemetry an endpoint accepted:
  * run --save-responses FILE   what the endpoint RETURNED to each request (status + body)
  * run -v                      stream every request's response line as it happens
  * detect <ingest-log>         what the endpoint INGESTED, classified by technique

Only point this at 'hyperject mock' or infrastructure you are authorized to test.
"""

RUN_EPILOG = """\
reviewing the results:
  results.json          per-technique acceptance (sent / accepted / errors / status codes)
  --save-responses FILE the raw HTTP response from each endpoint, for manual review
  -v                    prints 'METHOD url -> STATUS body' for every request live

examples:
  # send everything to the mock endpoint and record what it returned
  hyperject run --target-base http://127.0.0.1:8080 --save-responses responses.json

  # watch one endpoint's responses live while checking a single technique
  hyperject run -m app_insights -t bulk -v

  # preview the exact payloads without sending (offline detection building)
  hyperject run --dry-run -t covert

  # gate CI on the endpoint accepting every technique
  hyperject run --require-accept
"""


def _color_parent() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    g = common.add_argument_group("output")
    g.add_argument("--color", choices=("auto", "always", "never"), default="auto",
                   help="colorize output (default: auto — on when writing to a terminal)")
    g.add_argument("--no-color", action="store_const", const="never", dest="color",
                   help="disable colored output (same as --color never)")
    return common


def build_parser() -> argparse.ArgumentParser:
    common = _color_parent()
    p = argparse.ArgumentParser(
        prog="hyperject",
        formatter_class=RawFmt,
        description=ui.banner("send telemetry-injection traffic, then review what "
                              "the endpoint accepted") + "\n\n" +
                    "Config-driven, plugin modules & middleware, no built-in targets.",
        epilog=TOP_EPILOG)
    p.add_argument("--version", action="version", version=f"hyperject {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="<command>")

    # ---- run -------------------------------------------------------------- #
    r = sub.add_parser(
        "run", formatter_class=RawFmt, parents=[common],
        help="send telemetry to the endpoint(s) and record what came back",
        description="Send each module's telemetry-injection techniques to its "
                    "configured endpoint and record what the endpoint accepted, so "
                    "you can review its behaviour and validate detections.",
        epilog=RUN_EPILOG)

    g_tgt = r.add_argument_group("what to send and where")
    g_tgt.add_argument("-c", "--config", default="config.json",
                       help="config file describing the endpoints to check (default: config.json)")
    g_tgt.add_argument("-m", "--modules", dest="modules_filter", nargs="*", metavar="MODULE",
                       help="only check these endpoint modules (default: all enabled)")
    g_tgt.add_argument("-t", "--techniques", nargs="*", choices=VARIANTS, metavar="TECHNIQUE",
                       help=f"only send these techniques (default: all — {', '.join(VARIANTS)})")
    g_tgt.add_argument("--target-base", metavar="URL",
                       help="send ALL modules to this host instead of the config's, "
                            "preserving each path — e.g. http://127.0.0.1:8080")

    g_rev = r.add_argument_group("reviewing the endpoint's telemetry")
    g_rev.add_argument("--transcript", metavar="FILE",
                       help="record the FULL request+response of every exchange to FILE "
                            "(format set by --export) for review")
    g_rev.add_argument("--export", choices=FORMATS, default="json", metavar="FORMAT",
                       help=f"transcript format: {', '.join(FORMATS)} (default: json; "
                            "'har' opens in Burp/Chrome, 'pretty' is colorized)")
    g_rev.add_argument("--save-responses", metavar="FILE",
                       help="record just each endpoint's response (status + body) to FILE")
    g_rev.add_argument("--output", metavar="FILE",
                       help="where to write the per-technique acceptance summary "
                            "(default: results.json / config 'output')")
    g_rev.add_argument("--format", choices=("table", "json"), default="table",
                       help="on-screen summary style (default: table)")
    g_rev.add_argument("-v", "--verbose", action="store_true",
                       help="stream each request's endpoint response as it happens")
    g_rev.add_argument("-q", "--quiet", action="store_true", help="suppress progress output")
    g_rev.add_argument("--require-accept", action="store_true",
                       help="exit non-zero unless the endpoint accepted every technique "
                            "(use as a detection/coverage gate in CI)")
    g_rev.add_argument("--dry-run", action="store_true",
                       help="print the exact payloads and send NOTHING (offline review)")

    g_net = r.add_argument_group("proxy & transport")
    g_net.add_argument("--proxy", metavar="URL",
                       help="route all traffic through an HTTP(S) proxy, e.g. Burp/mitmproxy "
                            "at http://127.0.0.1:8080 (or set config run.proxy)")
    g_net.add_argument("--insecure", action="store_true",
                       help="disable TLS certificate verification (needed behind an "
                            "intercepting proxy)")
    g_net.add_argument("--max-attempts", type=int, metavar="N",
                       help="hard cap on send attempts per request when retry "
                            "middleware is active (default: config run.max_attempts or 4)")

    g_vol = r.add_argument_group("volume & timing (load / rate behaviour)")
    g_vol.add_argument("--count", type=int, metavar="N",
                       help="events per 'bulk' technique (default: config run.count)")
    g_vol.add_argument("--concurrency", type=int, default=1, metavar="N",
                       help="parallel senders — raise to test the endpoint under load")
    g_vol.add_argument("--repeat", type=int, default=1, metavar="N",
                       help="run N full passes (continuous/soak simulation)")
    g_vol.add_argument("--interval", type=float, default=0, metavar="S",
                       help="seconds to wait between --repeat passes")
    g_vol.add_argument("--timeout", type=float, metavar="S",
                       help="per-request timeout in seconds (default: config run.timeout)")
    g_vol.add_argument("--delay", type=float, metavar="S",
                       help="delay between requests in seconds (default: config run.rate_limit_delay)")
    g_vol.add_argument("--seed", type=int, metavar="N",
                       help="fix the RNG seed so payloads are reproducible across runs")
    r.set_defaults(func=cmd_run)

    # ---- list ------------------------------------------------------------- #
    l = sub.add_parser("list", formatter_class=RawFmt, parents=[common],
                       help="show the modules, techniques, and middleware available",
                       description="List the discovered endpoint modules (plugins), the "
                                   "injection techniques each supports, and the middleware.")
    l.add_argument("--modules-only", action="store_true", help="show only modules")
    l.add_argument("--techniques-only", action="store_true", help="show only techniques")
    l.add_argument("--middleware-only", action="store_true", help="show only middleware")
    l.set_defaults(func=cmd_list)

    # ---- init ------------------------------------------------------------- #
    i = sub.add_parser("init", formatter_class=RawFmt, parents=[common],
                       help="scaffold a config.json describing the endpoints to check",
                       description="Generate a config.json from the discovered modules, with "
                                   "targets pointed at the local mock collector by default.")
    i.add_argument("-o", "--output", default="config.json", metavar="FILE",
                   help="config file to write (default: config.json)")
    i.add_argument("--target-base", default="http://127.0.0.1:8080", metavar="URL",
                   help="base URL to point the generated endpoints at (default: mock collector)")
    i.add_argument("--force", action="store_true", help="overwrite an existing config file")
    i.set_defaults(func=cmd_init)

    # ---- validate --------------------------------------------------------- #
    v = sub.add_parser("validate", formatter_class=RawFmt, parents=[common],
                       help="check the config's endpoints/keys without sending anything",
                       description="Confirm the config is complete (no placeholder targets/keys "
                                   "and no unknown modules) before you send traffic.")
    v.add_argument("-c", "--config", default="config.json", metavar="FILE",
                   help="config file to check (default: config.json)")
    v.set_defaults(func=cmd_validate)

    # ---- mock ------------------------------------------------------------- #
    mk = sub.add_parser("mock", formatter_class=RawFmt, parents=[common],
                        help="run a safe local endpoint that logs the telemetry it receives",
                        description="Start a local stand-in endpoint that mimics the ingest "
                                    "APIs and logs every request to JSONL for later review with "
                                    "'hyperject detect'. Use this as a safe target.")
    mk.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    mk.add_argument("--port", type=int, default=8080, help="listen port (default: 8080)")
    mk.add_argument("--log", default="ingest.log.jsonl", metavar="FILE",
                    help="where to log received telemetry (default: ingest.log.jsonl)")
    mk.set_defaults(func=cmd_mock)

    # ---- detect ----------------------------------------------------------- #
    d = sub.add_parser("detect", formatter_class=RawFmt, parents=[common],
                       help="review an endpoint's ingest log and classify what it accepted",
                       description="Read an endpoint's telemetry/ingest log (JSONL) and report "
                                   "which injection techniques got through — unauthenticated "
                                   "ingest, floods, oversized payloads, covert-field C2. "
                                   "Anything sent but not flagged here is a detection gap.")
    d.add_argument("log", nargs="?", default="ingest.log.jsonl", metavar="INGEST_LOG",
                   help="telemetry log to review (default: ingest.log.jsonl from 'hyperject mock')")
    d.set_defaults(func=cmd_detect)

    # ---- capture ---------------------------------------------------------- #
    cap = sub.add_parser(
        "capture", formatter_class=RawFmt, parents=[common],
        help="show the real OTLP request+response (and diff vs the OpenTelemetry SDK)",
        description="Send one OTLP payload and print the exact request and response. "
                    "Build it with hyperject's own encoders (JSON or built-in "
                    "protobuf) or drive the real OpenTelemetry SDK, against a local "
                    "in-process capture server (default), a --target, or via --proxy.",
        epilog="examples:\n"
               "  hyperject capture --encoding protobuf        # our protobuf, shown decoded\n"
               "  hyperject capture --source sdk               # what the real OTel SDK emits\n"
               "  hyperject capture --diff                     # fidelity: hyperject vs SDK\n"
               "  hyperject capture --target http://otel:4318  # hit a real collector\n")
    cap.add_argument("--source", choices=("hyperject", "sdk"), default="hyperject",
                     help="hyperject encoders (default) or the real OpenTelemetry SDK")
    cap.add_argument("--signal", choices=("traces", "metrics", "logs"), default="traces",
                     help="OTLP signal to send (default: traces)")
    cap.add_argument("--encoding", choices=("json", "protobuf"), default="protobuf",
                     help="wire encoding for --source hyperject (default: protobuf)")
    cap.add_argument("--target", metavar="URL",
                     help="OTLP/HTTP root to send to (default: local capture server)")
    cap.add_argument("--service-name", default="hyperject-capture", metavar="NAME",
                     help="service.name resource attribute (default: hyperject-capture)")
    cap.add_argument("--diff", action="store_true",
                     help="build with BOTH hyperject and the real SDK and compare them")
    cap.add_argument("--proxy", metavar="URL",
                     help="route through an HTTP(S) proxy (Burp/mitmproxy/ZAP)")
    cap.add_argument("--insecure", action="store_true",
                     help="disable TLS verification (needed behind an intercepting proxy)")
    cap.set_defaults(func=cmd_capture)

    # ---- export ----------------------------------------------------------- #
    e = sub.add_parser("export", formatter_class=RawFmt, parents=[common],
                       help="beautify / convert a saved transcript, responses, or any JSON",
                       description="Pretty-print (colorized) or convert a saved file. Works on "
                                   "any JSON/JSONL (results.json, responses.json, config.json); "
                                   "transcripts additionally convert to har / jsonl / json.")
    e.add_argument("file", metavar="FILE", help="the JSON/JSONL file to read")
    e.add_argument("--format", choices=FORMATS, default="pretty",
                   help=f"output format: {', '.join(FORMATS)} (default: pretty = colorized JSON)")
    e.add_argument("-o", "--output", metavar="FILE",
                   help="write to FILE instead of stdout")
    e.set_defaults(func=cmd_export)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    ui.set_color_mode(getattr(args, "color", "auto"))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
