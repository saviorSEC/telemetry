# Reviewing OpenTelemetry / Azure Monitor services

These integrations let hyperject review the **OpenTelemetry ingestion path** the
same way it reviews the legacy telemetry endpoints: send well-formed traffic,
then read back the per-target verdict (`EXPOSED` / `auth-required` / `rejected`).

All of them obey the project safety model — no built-in targets or credentials,
default to the mock collector, and refuse to run against `REPLACE_` placeholders.

## The data path these modules mirror

An app instrumented with the **OpenTelemetry SDK** reaches a backend one of two
ways, and hyperject has a module for each:

| Path | Wire format | Module |
|------|-------------|--------|
| App → **OTLP collector** | OTLP/HTTP: `POST /v1/{traces,metrics,logs}`, JSON **or binary protobuf**, port 4318 | [`otlp`](#otlp-module) |
| App → **Azure Monitor OTel exporter** → Application Insights | "Breeze" envelopes to `{IngestionEndpoint}/v2.1/track` | [`azmon_breeze`](#azure-monitor-breeze-module) |
| App → **Azure Monitor Live Metrics** | QuickPulse: `POST {LiveEndpoint}/QuickPulseService.svc/{ping,post}` | [`live_metrics`](#live-metrics--quickpulse-module) |

Adjacent Azure Monitor surfaces are covered too: **connection strings** (how the
exporter is addressed, incl. `IngestionEndpoint` and `LiveEndpoint`) and
**availability web-tests** (the ARM control plane). And [`hyperject
capture`](#hyperject-capture--real-sdk--fidelity) drives the **real OpenTelemetry
SDK** to show and validate the genuine wire traffic.

## OTLP module

Exercises an OpenTelemetry collector / OTLP-compatible endpoint. `base_url` is
the OTLP/HTTP root (real collectors listen on `:4318`); the signal paths
`/v1/traces`, `/v1/metrics`, `/v1/logs` are appended. The OTLP spec leaves auth
to the deployment (arbitrary headers such as `OTEL_EXPORTER_OTLP_HEADERS`), so a
collector that accepts unauthenticated OTLP is `EXPOSED`.

```json
"otlp": {
  "enabled": true,
  "base_url": "http://127.0.0.1:8080",
  "signals": ["traces", "metrics", "logs"],
  "service_name": "hyperject-bas",
  "headers": {}
}
```

- **Verdict mapping:** `200` (no `partialSuccess`) → `EXPOSED`; `401/403` →
  `auth-required`; `400` → `rejected`.
- Set `headers` (e.g. `{"Authorization": "Bearer TEST"}`) to probe a collector
  that should require auth.
- `covert` hides the marker in a span/log/metric attribute keyed by
  `techniques.covert_field.field`; `large` inflates an attribute value.

### JSON vs binary protobuf

Real collectors and the OTLP/gRPC endpoint speak **binary protobuf**, not JSON.
Set `"encoding": "protobuf"` to send `application/x-protobuf` — hyperject ships a
small dependency-free protobuf codec ([`hyperject.proto`](../src/hyperject/proto.py))
that hand-encodes the OTLP `Export{Traces,Metrics,Logs}ServiceRequest` messages
and decodes the `Export*ServiceResponse` / `Status` that comes back. No
`protobuf` or `opentelemetry-proto` install required. (The bytes it produces
parse cleanly under the real `opentelemetry-proto` — see `hyperject capture
--diff`.)

```json
"otlp": { "enabled": true, "base_url": "http://collector:4318",
          "encoding": "protobuf", "signals": ["traces", "metrics", "logs"] }
```

Protobuf request bodies are rendered in transcripts/exports as a
`{"_encoding": "binary", "bytes": N, "base64": "..."}` marker so `--transcript`,
`--save-responses`, and `hyperject export` keep working on binary traffic.

> **gRPC (port 4317):** the synthetic `otlp` module is OTLP/**HTTP** (JSON or
> protobuf). To exercise OTLP/gRPC, use the real gRPC exporter through
> `hyperject capture` (see below), which speaks HTTP/2 + gRPC framing.

## Live Metrics / QuickPulse module

`live_metrics` exercises the connection string's **`LiveEndpoint`** — the
real-time Live Metrics stream. Clients subscribe with
`POST {LiveEndpoint}/QuickPulseService.svc/ping?ikey=<ikey>` and stream
`MonitoringDataPoint`s to `.../post`, authenticated only by the ikey query param
and `x-ms-qps-*` headers. An endpoint that accepts unauthenticated QuickPulse is
`EXPOSED`.

```json
"live_metrics": {
  "enabled": true,
  "endpoints": ["http://127.0.0.1:8080"],
  "ikeys": ["REPLACE_WITH_YOUR_OWN_TEST_IKEY"],
  "connection_strings": [],
  "actions": ["ping", "post"]
}
```

Paste a connection string under `connection_strings` and hyperject derives the
`LiveEndpoint` (explicit, or `live.<EndpointSuffix>`) and ikey for you.

## Azure Monitor Breeze module

The Azure Monitor OpenTelemetry exporter does **not** send OTLP to Azure — it
maps OTel signals into Application Insights "Breeze" envelopes and POSTs them to
`{IngestionEndpoint}/v2.1/track`:

```
OTel server span  -> RequestData          OTel log record -> MessageData
OTel client span  -> RemoteDependencyData  OTel metric     -> MetricData
```

`azmon_breeze` sends those exact envelope shapes (the sibling `app_insights`
module sends raw `EventData`). `envelope_types` selects which to send. Reuses the
`itemsAccepted` acceptance contract.

```json
"azmon_breeze": {
  "enabled": true,
  "endpoints": ["http://127.0.0.1:8080/v2.1/track"],
  "ikeys": ["REPLACE_WITH_YOUR_OWN_TEST_IKEY"],
  "connection_strings": [],
  "envelope_types": ["RequestData", "RemoteDependencyData", "MessageData"]
}
```

### Connection strings

Instead of an endpoint + ikey, paste an **Azure Monitor connection string** — the
same value the exporter is configured with. hyperject parses it into the ikey and
the `/v2.1/track` ingestion URL (explicit `IngestionEndpoint` wins; otherwise
`dc.<EndpointSuffix>` is derived). The embedded ikey is still checked against the
placeholder guard.

```json
"connection_strings": [
  { "value": "InstrumentationKey=<guid>;IngestionEndpoint=https://<region>.in.applicationinsights.azure.com/",
    "label": "my-app" }
]
```

> Ikeys are addressing identifiers, not security tokens — which is exactly why
> anonymous ingestion is worth reviewing. Enforce auth with Microsoft Entra.

### Agent-evaluation poisoning (`covert`)

Azure AI Foundry **continuous agent evaluation** writes results to Application
Insights as a `MessageData` whose `message` is `gen_ai.evaluation.result`, with
`gen_ai.*` custom dimensions (`gen_ai.thread.run.id`, scores, etc.). The `covert`
variant forges one of these envelopes — demonstrating how an exposed ingestion
endpoint lets an attacker inject **fake evaluation scores** into an agent
observability dashboard. The detector flags it as `GENAI_EVAL_POISON`.

## Availability web-test module (control plane)

`availability_webtest` is **not** telemetry ingestion — it exercises the Azure
Resource Manager control plane: `PUT .../Microsoft.Insights/webtests/{name}`
(api-version `2022-06-15`), which provisions a synthetic ping/standard
availability test. Different trust model: ARM writes need a Microsoft Entra
bearer token, so the **secure outcome is `401/403`**. Disabled by default; fill
`subscription_id`/`resource_group`/`component_id` with values you own and set
`bearer_token` for an authorized create. Only `basic`/`bulk` apply.

## `hyperject capture` — real SDK + fidelity

Everything above sends payloads hyperject *builds*. `hyperject capture` closes
the loop by showing the exact request **and** response of an OTLP exchange, and
can drive the **genuine OpenTelemetry SDK** so you see what the real project puts
on the wire.

```bash
hyperject capture --encoding protobuf     # our protobuf, response decoded
hyperject capture --source sdk            # what the real OpenTelemetry SDK emits
hyperject capture --diff                  # fidelity: hyperject vs the real SDK
hyperject capture --target http://otel:4318   # hit a real collector
hyperject capture --proxy http://127.0.0.1:8080 --insecure   # through Burp/ZAP
```

By default traffic goes to a local in-process capture server, so both request
and response are shown even with no external endpoint. `--source sdk` and
`--diff` need the OpenTelemetry SDK:

```bash
pip install 'hyperject[otel]'
```

`--diff` emits the *same* span from both hyperject's protobuf codec and the real
SDK, then compares them — a `MATCH` verdict confirms hyperject's binary OTLP is
structurally the OTLP the SDK produces (the SDK additionally auto-adds
`telemetry.sdk.*` resource attributes, which is expected).

## Detector additions

`hyperject detect` classifies the new traffic in an ingest log:

| Finding | Meaning |
|---------|---------|
| `OTLP_INGEST` | An OTLP/HTTP export (`/v1/*` path or `resourceSpans`/`resourceMetrics`/`resourceLogs` body) was accepted; notes `json` vs `protobuf` |
| `QUICKPULSE_INGEST` | A Live Metrics / QuickPulse stream (`/QuickPulseService.svc/` or `x-ms-qps-*` headers) was accepted |
| `GENAI_EVAL_POISON` | A forged `gen_ai.evaluation.result` (agent-eval poisoning) was ingested |

These join the existing `UNAUTH_INGEST`, `OVERSIZED_PAYLOAD`, `COVERT_FIELD_C2`,
and `BULK_FLOOD` classifiers, keeping the detection half of the loop complete for
the OpenTelemetry modules.
