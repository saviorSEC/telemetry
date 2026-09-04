# Getting Started

[← Docs home](README.md)

## Requirements

- Python 3.10+
- `pipx` (recommended) or `pip`
- The only runtime dependency is `requests`.

## Install

```bash
# from the project root (the folder containing hyperject-main/)
pipx install ./hyperject-main
```

This puts a single `hyperject` command on your PATH. Verify:

```bash
hyperject --version
hyperject --help
```

For development (source edits take effect without reinstalling):

```bash
pipx install -e ./hyperject-main
```

Uninstall with `pipx uninstall hyperject`.

> If you edit the source and a change doesn't appear, clear stale build
> artifacts: `make clean` in `hyperject-main/`, then reinstall with
> `--pip-args=--no-cache-dir`.

## The full loop (against the safe mock)

hyperject is a closed loop: **send traffic → see what the endpoint did → confirm
your detections catch it.** The built-in mock collector is a safe target that
logs everything it receives.

```bash
# Terminal A — start the safe local endpoint
hyperject mock --port 8080 --log ingest.log.jsonl

# Terminal B
hyperject init                       # writes config.json (targets = the mock)
hyperject run                        # send every module's techniques
hyperject detect ingest.log.jsonl    # classify what got through
```

Expected result: `run` reports `EXPOSED` for each target (the mock accepts
everything), and `detect` flags the techniques (unauth ingest, bulk flood,
oversized payload, covert-field C2). Anything sent but **not** flagged by
`detect` is a detection coverage gap.

## Preview without sending

`--dry-run` builds and prints the exact payloads but sends nothing — ideal for
inspecting what a technique looks like or building detections offline:

```bash
hyperject run --dry-run -t covert
```

## Pointing at a real (authorized) target

1. Put your endpoint(s) and key(s) in `config.json` (see
   [Configuration](configuration.md)), **or** override the host at runtime:

   ```bash
   hyperject run --target-base https://host-you-are-authorized-to-test
   ```

2. Validate first — the tool refuses to run while any placeholder remains:

   ```bash
   hyperject validate
   ```

3. Run and keep a full record for review:

   ```bash
   hyperject run --transcript run.har --export har
   ```

See [Reviewing Results](reviewing-results.md) for how to read the output, and
[Concepts → Safety model](concepts.md#safety-model) before pointing anywhere.
