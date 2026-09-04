# hyperject

Unified **breach-and-attack-simulation (BAS)** tool for telemetry-injection
techniques, plus the detection half of the loop. Consolidates the per-target
PoCs in [`../source-files/`](../source-files/) into one config-driven package
with a **plugin module system** — each target is its own self-contained file,
mirroring how the source-files are organized.

**Full documentation / wiki:** [`docs/`](docs/README.md) — getting started,
concepts, command & config reference, modules, middleware, reviewing results,
extending, and the source-files key mapping.

## Safety model (important)

- **No built-in targets or credentials.** Every endpoint and key comes from
  *your* `config.json`. The tool refuses to run against placeholder values.
- Point it at the built-in **mock collector** (default) or an **authorized lab
  range you control** — never at third-party production infrastructure.
- `hyperject run --dry-run` builds and prints payloads without sending anything.

## Install (pipx)

```bash
pipx install ./hyperject-main          # from the project root
pipx install -e ./hyperject-main       # editable/dev mode (picks up source edits)
```

Installs a single `hyperject` command. Uninstall: `pipx uninstall hyperject`.

## Quick start

```bash
hyperject mock --port 8080 &     # 1. safe local target
hyperject init                   # 2. scaffold config.json from discovered modules
hyperject run                    #    (add --dry-run to preview)
hyperject detect ingest.log.jsonl  # 3. confirm every technique is detected
```

## Commands

```
hyperject run       generate injection traffic and record what came back
hyperject list      list discovered modules, techniques, and middleware
hyperject init      scaffold config.json from discovered modules
hyperject validate  check a config without sending
hyperject mock      run the local mock collector (safe target)
hyperject detect    review an ingest log and classify what got through
hyperject capture   show the real OTLP request+response (JSON/protobuf; diff vs the OTel SDK)
hyperject export    beautify / convert a transcript, responses, or any JSON
```

Run `hyperject <command> -h` for per-command options. Key `run` flags:
`--target-base URL`, `--transcript FILE --export {json,jsonl,har,pretty}`,
`--proxy URL`, `--insecure`, `--concurrency N`, `--repeat N --interval S`,
`--require-accept` (CI gate), `--dry-run`, `-m/-t` filters. Color everywhere via
`--color auto|always|never` (auto-off when piped or `NO_COLOR` is set).

## Reviewing how you interact with the telemetry

Ways to see exactly what happened on the wire:

| How | Shows | Command |
|-----|-------|---------|
| **Exposure verdict** | per-target `EXPOSED` / `auth-required` / `rejected` (acc/auth/rej/err columns) | run summary + `results.json` |
| **Full transcript** | complete request **and** response of every exchange | `hyperject run --transcript t.json` |
| **Raw responses** | just each endpoint's status + body | `hyperject run --save-responses responses.json` |
| **Live stream** | `METHOD url -> STATUS body` per request, colorized | `hyperject run -v` |
| **What was ingested** | techniques that got through, classified | `hyperject detect <ingest-log>` |

Each run classifies every response: **401/403 → `auth-required`** (the endpoint
is secure), an accepted status → **`EXPOSED`** (it took injected telemetry with
no required auth), anything else → **`rejected`**. That's the recon verdict the
original PoC scripts produce, now per target and per format.

```bash
# capture the full request/response transcript, export as HAR (open in Burp/Chrome)
hyperject run --target-base http://127.0.0.1:8080 --transcript run.har --export har

# beautify any saved file (colorized), or convert a transcript between formats
hyperject export run.har --format pretty
hyperject export transcript.json --format har -o out.har
hyperject export results.json                 # pretty-print any JSON/JSONL
```

Secrets listed under `transcript.redact` in the config are masked in every export.

## Proxy & middleware

Route all traffic through an intercepting proxy (Burp, mitmproxy, ZAP) for
manual review, and disable TLS verification for its CA:

```bash
hyperject run --proxy http://127.0.0.1:8080 --insecure
```

Middleware are auto-discovered plugins that intercept every exchange. They can
**mutate the request, short-circuit it (answer without sending), replace the
response, retry (bounded), or recover from a transport error** — the full hook
point for proxy-style tooling. Enable them per-config:

```json
"middleware": [
  {"name": "allowlist",       "options": {"hosts": ["127.0.0.1", "collector.lab"]}},
  {"name": "extra_headers",   "options": {"headers": {"Authorization": "Bearer TEST"}}},
  {"name": "tag_correlation", "options": {"header": "X-BAS-Run", "value": "run-42"}},
  {"name": "retry_on_status", "options": {"statuses": [429, 503], "max": 2}}
]
```

Built-ins: `allowlist` (safety — blocks any host not listed, no network hit),
`extra_headers`, `tag_correlation`, `retry_on_status`. `--max-attempts N` caps
total tries per request. `hyperject list --middleware-only` shows what's available.

### Writing middleware (the hook contract)

Drop a file in [`src/hyperject/middleware/`](src/hyperject/middleware/) subclassing
`Middleware`. Every hook receives a `RequestContext` (`ctx`):

| Hook | When | Can do |
|------|------|--------|
| `before_request(ctx)` | before sending | mutate `ctx.request`; `ctx.short_circuit(resp)` to skip the network |
| `after_response(ctx)` | after a response | read `ctx.response`; `ctx.replace_response(r)`; `ctx.retry()` |
| `on_error(ctx)` | on transport error | recover via `ctx.replace_response(r)` or `ctx.retry()` |
| `applies_to(ctx)` | filter | return `False` to skip this middleware for the exchange |

`ctx` exposes `request`, `response`, `error`, `attempt`, `module`, `technique`.
Set `priority` (lower runs earlier; hooks nest onion-style). Use
`SyntheticResponse(status, body, ...)` to inject/block a response.

```python
# src/hyperject/middleware/block_writes.py
from ..mwbase import Middleware, SyntheticResponse

class BlockWrites(Middleware):
    name = "block_writes"
    priority = 20
    def before_request(self, ctx):
        if ctx.request["method"] == "POST" and not self.options.get("allow_post"):
            ctx.short_circuit(SyntheticResponse(0, {"blocked": "write"}))
```

## Development

```bash
make dev      # editable install (source edits take effect immediately)
make test     # run the contract + unit test suite (pytest)
make loop     # full mock -> run -> detect review loop in ./.demo
make lint     # byte-compile all sources
make clean    # remove build artifacts and the demo dir
```

The test suite includes **contract tests that run against every discovered
module and middleware**, so a newly-added plugin file is automatically checked
(a target for valid `default_config()`/`plan()`, a middleware for a valid
`Middleware` subclass) — run `make test` after adding one. A guard test also
keeps the project **emoji-free** (plain typography is allowed; emoji are not).

## Adding a new target (the modular part)

Drop one file in [`src/hyperject/modules/`](src/hyperject/modules/) — no edits
to the engine, CLI, `init`, or `list`. It's auto-discovered on next run.

```python
# src/hyperject/modules/my_target.py
from ..base import TargetModule
from ..core import Prepared, variant_count

class MyTarget(TargetModule):
    name = "my_target"
    description = "my target ingest"
    supported_techniques = ("basic", "bulk")   # optional; defaults to all four

    def default_config(self, base_url):         # feeds `hyperject init`
        return {"enabled": True, "description": self.description,
                "endpoint": f"{base_url}/ingest"}

    def plan(self, mcfg, cfg, variants):        # build the requests
        url = mcfg["endpoint"]
        check = lambda r: r.status_code == 200
        out = []
        for v in variants:
            preps = [Prepared("POST", url, {"json": {"n": i}}, check)
                     for i in range(variant_count(v, cfg))]
            out.append((v, url, preps))
        return out
```

Then `hyperject list` shows it, `hyperject init` includes it, and `hyperject run`
executes it. External pip packages can also register targets via the
`hyperject.modules` entry-point group (see `pyproject.toml`).

## Package layout

```
hyperject-main/
├── pyproject.toml
├── Makefile                     # install / test / loop / clean tasks
├── config.example.json          # reference (hyperject init generates a live one)
├── docs/                        # documentation wiki (see docs/README.md)
├── examples/                    # filled-in example configs
├── tests/                       # pytest suite (unit + plugin contract + no-emoji guard)
└── src/hyperject/
    ├── cli.py                    # argparse + subcommands (banner, color, groups)
    ├── core.py                   # engine (proxy/middleware/transcript), config, payloads
    ├── ui.py                     # color, ASCII banner, JSON beautify
    ├── transcript.py             # request/response records + json/jsonl/har/pretty export
    ├── proto.py                  # dependency-free protobuf codec (OTLP, Prometheus, Loki, Zipkin)
    ├── snappy.py                 # dependency-free Snappy block encoder (Prometheus/Loki)
    ├── capture.py                # `hyperject capture` — real OTel SDK + fidelity diff
    ├── base.py                   # TargetModule contract
    ├── mwbase.py                 # Middleware contract
    ├── registry.py               # auto-discovery of modules + middleware
    ├── modules/                  # one self-contained file per target
    │   ├── checkin.py            #   device check-in (+ fleet-vehicle profile)
    │   ├── app_insights.py
    │   ├── one_collector.py      #   (+ browser Origin/Referer spoof)
    │   ├── otlp.py               #   OTLP/HTTP traces|metrics|logs (json + protobuf)
    │   ├── azmon_breeze.py       #   Azure Monitor OTel Breeze envelopes (+ gen_ai poison)
    │   ├── live_metrics.py       #   Azure Monitor Live Metrics / QuickPulse
    │   ├── availability_webtest.py  # App Insights availability web-test (ARM)
    │   ├── prometheus_remote_write.py  # Prometheus remote write (protobuf + snappy)
    │   ├── loki.py               #   Grafana Loki push (protobuf + snappy / json)
    │   ├── zipkin.py             #   Zipkin v2 spans (protobuf / json)
    │   ├── kv_trace.py           #   json + form + tracking-pixel formats
    │   ├── pixel_analytics.py    #   GET pixel (full + minimal)
    │   ├── apple_metrics.py      #   json / native / plaintext / form
    │   └── facebook_pixel.py     #   GET pixel / POST form / CAPI json
    ├── middleware/               # one file per request/response plugin
    │   ├── allowlist.py
    │   ├── extra_headers.py
    │   ├── tag_correlation.py
    │   └── retry_on_status.py
    ├── collector.py              # mock target
    └── detector.py               # log detector
```
