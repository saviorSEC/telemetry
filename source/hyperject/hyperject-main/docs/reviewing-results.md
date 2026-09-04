# Reviewing Results

[← Docs home](README.md)

A run produces several complementary views of what happened on the wire.

| View | Answers | How |
|------|---------|-----|
| **Exposure verdict** | did the endpoint accept / require auth / reject? | run summary + `results.json` |
| **Full transcript** | the complete request **and** response of every exchange | `run --transcript t.json` |
| **Raw responses** | just each endpoint's status + body | `run --save-responses responses.json` |
| **Live stream** | each request's response as it happens | `run -v` |
| **What was ingested** | which techniques got through | `detect <ingest-log>` |

## The exposure verdict

Each response is classified — **401/403 → `auth-required`** (secure), an accepting
status → **`EXPOSED`**, anything else → **`rejected`** — and each target row gets a
verdict. The summary table:

```
module          technique sent  acc auth  rej  err  verdict       target
app_insights    basic        1    1    0    0    0  EXPOSED       https://.../v2.1/track [Power BI WFE]
apple_metrics   basic        1    0    1    0    0  auth-required https://.../metrics [json]
```

`results.json` is the machine-readable version (per-technique `sent` / `accepted`
/ `auth_required` / `rejected` / `errors` / `status_codes`).

Use `--require-accept` to make the process exit non-zero unless every technique
was accepted — a coverage gate for CI.

## Transcripts

`--transcript FILE` records the full request+response of every exchange, in the
format chosen by `--export`:

| Format | Use |
|--------|-----|
| `json` (default) | structured, machine-readable |
| `jsonl` | one exchange per line (stream into other tools) |
| `har` | open directly in Burp or Chrome DevTools |
| `pretty` | colorized, human-readable in the terminal |

```bash
hyperject run --transcript run.har --export har
```

Secrets listed under `transcript.redact` in the config are masked in every export.

## export — beautify / convert after the fact

`hyperject export` reads any saved JSON/JSONL and pretty-prints it (colorized), or
converts a transcript between formats:

```bash
hyperject export results.json                     # pretty-print any JSON
hyperject export run.json --format har -o run.har # transcript -> HAR
```

## detect — the blue-team half

`hyperject detect <ingest-log>` reads the endpoint's request log (the mock
collector writes one; adapt for real logs) and classifies which techniques got
through:

```
[+] UNAUTH_INGEST      (63 hits)
[+] BULK_FLOOD          (5 hits)
[+] OVERSIZED_PAYLOAD   (3 hits)
[+] COVERT_FIELD_C2     (3 hits)
```

Anything you **sent** in the run but that does **not** appear here is a detection
coverage gap to close in your real pipeline. This is the point of the loop: not
just "can I inject?" but "would we catch it?".
