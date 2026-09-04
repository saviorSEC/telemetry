# Commands

[← Docs home](README.md)

```
hyperject <command> [options]
```

| Command | Purpose |
|---------|---------|
| [`run`](#run) | send telemetry and record what came back |
| [`list`](#list) | list modules, techniques, and middleware |
| [`init`](#init) | scaffold a `config.json` |
| [`validate`](#validate) | check a config without sending |
| [`mock`](#mock) | run the safe local collector |
| [`detect`](#detect) | review an ingest log and classify what got through |
| [`capture`](#capture) | show the real OTLP request+response; diff vs the OpenTelemetry SDK |
| [`export`](#export) | beautify / convert a transcript, responses, or any JSON |

Global: `--version`. Every subcommand accepts `--color auto|always|never`
(and `--no-color`); color is auto-off when output is piped or `NO_COLOR` is set.
Run `hyperject <command> -h` for the built-in help.

## run

Send each enabled module's techniques to its configured endpoint and classify
every response.

**What to send and where**

| Flag | Meaning |
|------|---------|
| `-c, --config PATH` | config file (default `config.json`) |
| `-m, --modules M...` | only these modules (default: all enabled) |
| `-t, --techniques T...` | only these techniques: `basic bulk large covert` |
| `--target-base URL` | send ALL modules to this host, preserving each path |

**Reviewing the endpoint's telemetry**

| Flag | Meaning |
|------|---------|
| `--transcript FILE` | record the full request+response of every exchange |
| `--export FORMAT` | transcript format: `json` `jsonl` `har` `pretty` (default `json`) |
| `--save-responses FILE` | record just each endpoint's status + body |
| `--output FILE` | acceptance summary path (default `results.json`) |
| `--format table\|json` | on-screen summary style |
| `-v` / `-q` | stream each response live / quiet |
| `--require-accept` | exit non-zero unless every technique was accepted (CI gate) |
| `--dry-run` | print payloads, send nothing |

**Proxy & transport**

| Flag | Meaning |
|------|---------|
| `--proxy URL` | route all traffic through an HTTP(S) proxy (Burp/mitmproxy/ZAP) |
| `--insecure` | disable TLS verification (needed behind an intercepting proxy) |
| `--max-attempts N` | hard cap on tries per request when retry middleware is active |

**Volume & timing**

| Flag | Meaning |
|------|---------|
| `--count N` | events per `bulk` technique |
| `--concurrency N` | parallel senders |
| `--repeat N` / `--interval S` | N passes, S seconds apart (soak) |
| `--timeout S` / `--delay S` | per-request timeout / delay |
| `--seed N` | fix the RNG for reproducible payloads |

```bash
hyperject run --target-base http://127.0.0.1:8080 --transcript run.har --export har
hyperject run -m app_insights -t bulk -v
hyperject run --require-accept || echo "coverage gap"
```

## list

```bash
hyperject list                 # techniques + modules + middleware
hyperject list --modules-only
hyperject list --techniques-only
hyperject list --middleware-only
```

## init

Scaffold a `config.json` from the discovered modules (targets default to the
mock collector).

| Flag | Meaning |
|------|---------|
| `-o, --output FILE` | config file to write (default `config.json`) |
| `--target-base URL` | base URL for the generated targets |
| `--force` | overwrite an existing file |

## validate

Confirm the config is complete — no placeholder targets/keys, no unknown modules.
Exit code is non-zero when invalid.

```bash
hyperject validate -c config.json
```

## mock

Run a safe local endpoint that mimics the ingest APIs and logs every request to
JSONL for later review with `detect`.

| Flag | Meaning |
|------|---------|
| `--host` | bind address (default `127.0.0.1`) |
| `--port` | listen port (default `8080`) |
| `--log FILE` | where to log received telemetry (default `ingest.log.jsonl`) |

## detect

Read an endpoint's ingest log (JSONL) and report which techniques got through —
unauthenticated ingest, bulk floods, oversized payloads, covert-field C2.

```bash
hyperject detect ingest.log.jsonl
```

## capture

Send one OTLP payload and print the exact request and response. Build it with
hyperject's own encoders (JSON or the built-in protobuf codec) or drive the real
OpenTelemetry SDK, against a local in-process capture server (default), a
`--target`, or through `--proxy`. See [OpenTelemetry / Azure
Monitor](opentelemetry.md#hyperject-capture--real-sdk--fidelity).

| Flag | Meaning |
|------|---------|
| `--source hyperject\|sdk` | our encoders (default) or the real OpenTelemetry SDK |
| `--signal traces\|metrics\|logs` | OTLP signal (default `traces`) |
| `--encoding json\|protobuf` | wire encoding for `--source hyperject` (default `protobuf`) |
| `--target URL` | OTLP/HTTP root to send to (default: local capture server) |
| `--diff` | build with BOTH sources and compare (fidelity check) |
| `--proxy URL` / `--insecure` | route through Burp/ZAP; skip TLS verify |

`--source sdk` and `--diff` need the OpenTelemetry SDK: `pip install 'hyperject[otel]'`.

```bash
hyperject capture --encoding protobuf     # our protobuf, response decoded
hyperject capture --diff                  # hyperject vs the real OTel SDK
```

## export

Beautify (colorized) or convert a saved file. Works on any JSON/JSONL
(`results.json`, `responses.json`, `config.json`); transcripts additionally
convert to `har` / `jsonl` / `json`.

| Flag | Meaning |
|------|---------|
| `--format FORMAT` | `pretty` (default, colorized) `json` `jsonl` `har` |
| `-o, --output FILE` | write to a file instead of stdout |

```bash
hyperject export results.json                    # pretty-print any JSON
hyperject export run.json --format har -o run.har
```
