# Other telemetry protocols (Prometheus, Loki, Zipkin)

Beyond the OpenTelemetry / Azure Monitor surfaces (see
[OpenTelemetry / Azure Monitor](opentelemetry.md)), hyperject reviews the other
widely-deployed **protobuf** telemetry ingest protocols. Like OTLP, all three
treat authentication as a transport-layer concern, so an endpoint that accepts an
unauthenticated write is `EXPOSED`.

All payloads are built with hyperject's own dependency-free protobuf codec
([`proto.py`](../src/hyperject/proto.py)); the two protocols that require Snappy
use the built-in Snappy block encoder ([`snappy.py`](../src/hyperject/snappy.py)),
so **no `protobuf`, `snappy`, or vendor client libraries are needed.**

| Module | Endpoint | Wire format | Success |
|--------|----------|-------------|---------|
| [`prometheus_remote_write`](#prometheus-remote-write) | `/api/v1/write` | protobuf **+ Snappy** | 2xx |
| [`loki`](#grafana-loki) | `/loki/api/v1/push` | protobuf+Snappy **or** JSON | 2xx |
| [`zipkin`](#zipkin) | `/api/v2/spans` | protobuf **or** JSON | 202 |

## Why these (and not others)

OTLP is the convergence protocol for the OpenTelemetry ecosystem, so the `otlp`
module already covers OTLP-based backends (Tempo, Honeycomb, New Relic, Datadog's
OTLP intake, Grafana Cloud, ...). The three above are the remaining
**non-OTLP protobuf** ingest surfaces with a large install base. Deliberately
**not** included: Jaeger (Thrift, converging on OTLP), OpenCensus (deprecated in
favor of OTLP), and the Datadog agent intake (msgpack, not protobuf) — they would
each need a different serializer for little added coverage. OTLP profiles
(`/v1development/profiles`) are deferred until the schema stabilizes.

## Prometheus Remote Write

How Prometheus, Grafana Mimir, Cortex, Thanos and VictoriaMetrics receive
metrics. `POST /api/v1/write` with a Snappy-compressed `prometheus.WriteRequest`
and headers `Content-Type: application/x-protobuf`, `Content-Encoding: snappy`,
`X-Prometheus-Remote-Write-Version: 0.1.0`.

```json
"prometheus_remote_write": {
  "enabled": true,
  "endpoint": "http://collector/api/v1/write",
  "job": "hyperject-bas",
  "headers": {}
}
```

- `covert` adds a label whose name is `techniques.covert_field.field` carrying the
  marker; `large` adds an oversized label value; `bulk` floods `run.count` writes.
- Add `headers` (e.g. `{"Authorization": "Bearer TEST"}`) to probe an
  authenticated receiver.

## Grafana Loki

Log ingestion at `POST /loki/api/v1/push`. `"encoding": "protobuf"` sends a
Snappy-compressed `logproto.PushRequest`; `"encoding": "json"` sends the
`{"streams": [{"stream": {..labels..}, "values": [[ts_ns, line]]}]}` form (Loki
requires the nanosecond timestamp as a **string**). Multi-tenant Loki keys off
`X-Scope-OrgID` — set `org_id` to send it.

```json
"loki": {
  "enabled": true,
  "endpoint": "http://loki/loki/api/v1/push",
  "encoding": "protobuf",
  "org_id": "",
  "labels": { "job": "hyperject-bas", "level": "info" }
}
```

## Zipkin

Trace collector at `POST /api/v2/spans` (returns `202 Accepted`). `"encoding":
"json"` sends a list of span objects; `"encoding": "protobuf"` sends a
`zipkin.proto3` `ListOfSpans`. `covert`/`large` ride in span tags.

```json
"zipkin": {
  "enabled": true,
  "endpoint": "http://zipkin/api/v2/spans",
  "encoding": "json",
  "service_name": "hyperject-bas"
}
```

## Detector additions

`hyperject detect` classifies each protocol in an ingest log:

| Finding | Meaning |
|---------|---------|
| `REMOTE_WRITE_INGEST` | A Prometheus remote-write (`/api/v1/write`) was accepted |
| `LOKI_INGEST` | A Grafana Loki push (`/loki/api/v1/push`) was accepted |
| `ZIPKIN_INGEST` | Zipkin spans (`/api/v2/spans`) were accepted |

Because the Snappy blocks store their payload uncompressed (all-literal), the
label/line/tag text — including any covert marker — is present verbatim on the
wire, so `UNAUTH_INGEST`, `COVERT_FIELD_C2`, `OVERSIZED_PAYLOAD`, and `BULK_FLOOD`
continue to fire on these modules too.
