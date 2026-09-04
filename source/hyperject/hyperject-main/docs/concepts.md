# Concepts

[← Docs home](README.md)

## What it does

hyperject probes a telemetry-ingest endpoint the way the original `source-files/`
PoCs do — sending crafted events and observing whether the endpoint **accepts**
them, **requires authentication**, or **rejects** them — and adds the tooling to
make that repeatable and reviewable: a mock target, a detector, transcripts,
proxy/middleware, and a plugin system.

## The workflow

```
  init --> (edit config) --> validate --> run --> review --> detect
                                           |        |          |
                                      exposure   transcript  coverage
                                       verdict    / export     gaps
```

1. **init** — scaffold a `config.json` from the discovered modules.
2. **validate** — confirm every target/key is filled (no placeholders).
3. **run** — send each module's techniques; classify every response.
4. **review** — read the verdict, the transcript, or exported HAR.
5. **detect** — over the endpoint's ingest log, confirm your detections fire.

## Two axes: techniques × formats

A **technique** is *how aggressive/sneaky* the payload is:

| Technique | Meaning |
|-----------|---------|
| `basic`   | a single, well-formed event |
| `bulk`    | N events (`run.count`) — flood / volume simulation |
| `large`   | an oversized payload (`techniques.large_payload_bytes`) |
| `covert`  | data hidden in a telemetry field (covert-channel / C2 simulation) |

A **format** is *how the payload is encoded* — JSON, form-urlencoded, plaintext,
GET tracking-pixel, etc. Modules that probe an endpoint's tolerance (e.g.
`kv_trace`, `apple_metrics`, `facebook_pixel`) emit one row per format so you can
see which encodings the endpoint accepts. See [Modules](modules.md).

## The exposure verdict

Every response is classified, and each target gets a verdict:

| Verdict | Meaning |
|---------|---------|
| `EXPOSED` | the endpoint **accepted** injected telemetry with no required auth |
| `auth-required` | the endpoint answered **401/403** — it required auth (secure) |
| `rejected` | some other non-accepting status |

This is the recon question the source scripts answer, now produced per target and
per format. See [Reviewing Results](reviewing-results.md).

## Architecture

```
cli.py           argparse, subcommands, colorized output, ASCII banner
core.py          HTTP engine (proxy/middleware/transcript/retry), config, payloads
registry.py      auto-discovery of modules + middleware (folder + entry points)
base.py          TargetModule contract          mwbase.py   Middleware contract
modules/*        one file per target             middleware/*  one file per hook
transcript.py    request/response records + json/jsonl/har/pretty export
collector.py     the safe mock endpoint          detector.py   log-based blue-team check
ui.py            color, banner, JSON beautify
```

Everything target-specific lives in `modules/`; everything hook-specific lives in
`middleware/`. Both are **auto-discovered** — drop in a file and it registers.
See [Extending](extending.md).

## Safety model

hyperject is built so it can't quietly attack production:

- **No built-in targets or credentials.** Every endpoint and key comes from your
  `config.json`. The tool refuses to run while any placeholder (`REPLACE_`,
  `YOUR_`, `CHANGEME`) remains.
- **A safety allowlist.** The `allowlist` middleware blocks any request whose host
  isn't explicitly listed — *before* it touches the network (see
  [Middleware](middleware.md)).
- **Dry-run.** `--dry-run` prints payloads and sends nothing.
- **Redaction.** `transcript.redact` masks secrets in exported records.

Only point hyperject at the built-in mock collector or infrastructure you are
**authorized** to test. Real production hostnames, real instrumentation/API keys,
and real device fingerprints are intentionally **not** shipped — you supply the
ones you're allowed to use.
