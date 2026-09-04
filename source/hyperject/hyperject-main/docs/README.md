# hyperject — Documentation

**hyperject** sends telemetry-injection traffic to a target endpoint, then lets
you review exactly what the endpoint accepted — for breach-and-attack simulation
(BAS) and detection engineering. It is config-driven, plugin-based, and ships
with **no built-in targets or credentials**: it only ever runs against what you
put in `config.json`.

```
 _                                _           _
| |__  _   _ _ __   ___ _ __     (_) ___  ___| |_
| '_ \| | | | '_ \ / _ \ '__|    | |/ _ \/ __| __|
| | | | |_| | |_) |  __/ | |     | |  __/ (__| |_
|_| |_|\__, | .__/ \___|_| |  _/ |\___|\___|\__|
       |___/|_|            |__/
```

## Start here

```bash
pipx install ./hyperject-main
hyperject mock &          # a safe local endpoint that logs what it receives
hyperject init            # scaffold config.json
hyperject run             # send + get the exposure verdict
hyperject detect          # review what the endpoint ingested
```

## Table of contents

| Page | What it covers |
|------|----------------|
| [Getting Started](getting-started.md) | Install, the mock→run→detect loop, first real run |
| [Concepts](concepts.md) | Architecture, the safety model, techniques, the workflow |
| [Commands](commands.md) | Every subcommand and flag (`run`, `list`, `init`, `validate`, `mock`, `detect`, `export`) |
| [Configuration](configuration.md) | Full `config.json` schema reference |
| [Modules](modules.md) | The built-in target modules and what each sends |
| [OpenTelemetry / Azure Monitor](opentelemetry.md) | Reviewing OTLP collectors, the Azure Monitor OTel path, connection strings, and agent-eval poisoning |
| [Other telemetry protocols](other-telemetry.md) | Prometheus Remote Write, Grafana Loki, and Zipkin (protobuf + Snappy, no deps) |
| [Middleware](middleware.md) | The request/response hook contract and built-in middleware |
| [Reviewing Results](reviewing-results.md) | Verdicts, transcripts, exports, and the detector |
| [Extending](extending.md) | Add a target module or a middleware in one file |
| [Keys Mapping](keys.md) | How each `source-files/` credential maps to a config block |
| [Development](development.md) | Tests, Makefile, and release notes |

## Safety in one line

Only point hyperject at the built-in mock collector or infrastructure you are
authorized to test. See [Concepts → Safety model](concepts.md#safety-model).
