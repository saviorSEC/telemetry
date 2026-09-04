# Target Modules

[← Docs home](README.md)

Each module is a self-contained plugin in [`../src/hyperject/modules/`](../src/hyperject/modules/)
that knows how to talk to one kind of ingest endpoint. They are auto-discovered —
`hyperject list --modules-only` shows what's installed. Each maps to one of the
original `source-files/` PoCs.

| Module | Endpoint field | Method / formats | Techniques | Source PoC |
|--------|----------------|------------------|------------|------------|
| `checkin` | `base_url` | POST JSON | basic, bulk, large, covert | hyperject-goog.py |
| `app_insights` | `endpoints[]` + `ikeys[]` | POST JSON `/v2.1/track` | basic, bulk, large, covert | hyperject-msrc.py |
| `one_collector` | `endpoints[]` + `keys[]` | POST `/OneCollector/1.0/` | basic, bulk, large, covert | hyperject-msrc.py |
| `kv_trace` | `endpoint` | POST json / form-kv / pixel | basic, bulk | test_service_trace.py |
| `pixel_analytics` | `endpoint` | GET pixel (full / minimal) | basic, bulk | test_program_analytics.py |
| `apple_metrics` | `endpoint` | POST json / native / text / form | basic, bulk | test_platform_metrics.py |
| `facebook_pixel` | `endpoint` | GET pixel / POST form / CAPI json | basic, bulk | test_software_pixel.py |

## checkin

Device check-in telemetry. Chooses a random `device_profiles` entry per event.
A profile with `"kind": "vehicle"` produces a dynamic `vehicle_id` plus
identity fields prefixed with `id_prefix` (the fleet/vehicle path). Acceptance:
`accept_field` truthy (default `stats_ok`).

## app_insights

App Insights `/v2.1/track`. Probes every `endpoint × iKey`. iKeys may be bare
GUIDs or annotated `{ikey,label}` objects (the label appears in results).
Acceptance: `itemsAccepted >= 1`.

## one_collector

OneCollector `/OneCollector/1.0/`. Probes every `endpoint × key`. Sends the
`apikey` query param, `iKey: o:<ikey>`, and spoofs the browser `Origin`/`Referer`
based on each key's `origin`. Acceptance: `accept_status` (default `204`).

## kv_trace

Key-value / trace ingest. Under `basic` it probes three encodings as separate
rows — JSON body, form-urlencoded key/value, and a form tracking-pixel
(`act`/`aid`). Acceptance: `200`/`204`.

## pixel_analytics

GET tracking-pixel analytics. Under `basic` it sends a full parameter set and a
minimal one. Acceptance: `200`.

## apple_metrics

Metrics ingest. Under `basic` it probes four encodings — basic JSON, a native
metrics-array, plain text, and form-urlencoded. Acceptance: `200`/`204`.

## facebook_pixel

Conversion pixel. Under `basic` it probes three ways — a GET tracking pixel, a
POST form, and a POST conversions-API JSON body (event + `user_data`).
Acceptance: `200`/`204`.

## Techniques applied

Modules that carry a body (`checkin`, `app_insights`, `one_collector`) support
all four techniques (`basic`, `bulk`, `large`, `covert`). The recon-style pixel
and metrics modules support `basic` (multi-format) and `bulk` (volume). See
[Concepts → Two axes](concepts.md#two-axes-techniques--formats).

To add your own target, see [Extending](extending.md).
