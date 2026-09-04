# Configuration

[← Docs home](README.md)

`config.json` is the entire control surface. Generate one with `hyperject init`,
edit it, then `hyperject validate`. A reference copy lives at
[`../config.example.json`](../config.example.json).

## Top-level shape

```json
{
  "run":        { ... },
  "modules":    { "<name>": { ... }, ... },
  "techniques": { ... },
  "middleware": [ ... ],
  "transcript": { ... }
}
```

Only `modules` is strictly required; the rest have sensible defaults. A module
that isn't present simply isn't run — a minimal config can contain a single
module. The tool **refuses to run** while any value contains a placeholder
(`REPLACE_`, `YOUR_`, `CHANGEME`).

## run

```json
"run": {
  "count": 10,               // events per 'bulk' technique
  "timeout": 10,             // per-request timeout (seconds)
  "rate_limit_delay": 0.2,   // delay between requests (seconds)
  "output": "results.json",  // acceptance-summary path
  "max_attempts": 4,         // hard cap on tries per request (retry middleware)
  "proxy": null              // "http://127.0.0.1:8080" to route through a proxy
}
```

CLI flags override these: `--count`, `--timeout`, `--delay`, `--output`,
`--max-attempts`, `--proxy`.

## modules

Each key is a module name (see [Modules](modules.md)); each value is that
module's block. Common fields:

| Field | Meaning |
|-------|---------|
| `enabled` | `false` to skip this module |
| `description` | free-text label |
| `base_url` **or** `endpoint` **or** `endpoints[]` | the target(s) |
| `accept_field` / `accept_status` | how an "accepted" response is recognized |

### Target fields by module

| Module | Target field | Keys |
|--------|--------------|------|
| `checkin` | `base_url` | — (`device_profiles`) |
| `app_insights` | `endpoints[]` | `ikeys[]` |
| `one_collector` | `endpoints[]` | `keys[]` (`key`/`ikey`/`origin`) |
| `apple_metrics`, `facebook_pixel`, `kv_trace`, `pixel_analytics` | `endpoint` | — |

### checkin device profiles

`device_profiles` is a list of devices; one is chosen at random per event. Keys
become `device_info` entries. A profile with `"kind": "vehicle"` gets a dynamic
`vehicle_id` and identity fields prefixed with `id_prefix` (the fleet path).

```json
"device_profiles": [
  { "device": "sim-device", "manufacturer": "sim-vendor", "model": "Sim", "sdk": "29" },
  { "device": "sim-vehicle", "manufacturer": "sim-fleet", "sdk": "30",
    "fleet": "sim-autonomous", "kind": "vehicle", "id_prefix": "FLEET" }
]
```

### App Insights iKeys (bare or annotated)

`ikeys` entries may be a bare GUID string **or** an annotated object so the label
shows in results. Every `endpoint × iKey` is probed.

```json
"app_insights": {
  "endpoints": ["https://host-a/v2.1/track", "https://host-b/v2.1/track"],
  "ikeys": [
    "11111111-2222-3333-4444-555555555555",
    { "ikey": "aaaaaaaa-...", "label": "Power BI WFE" }
  ],
  "accept_field": "itemsAccepted"
}
```

### OneCollector keys

Each key is `{ key, ikey, origin }`. If `origin` contains `portal` or `login`,
the matching browser `Origin`/`Referer` is spoofed automatically; or set
`origin_url` explicitly. Optional `label` shows in results.

```json
"one_collector": {
  "endpoints": ["https://host/OneCollector/1.0/"],
  "keys": [
    { "key": "<composite>", "ikey": "<ikey>", "origin": "portal.azure.com (Azure Portal)" }
  ],
  "accept_status": 204
}
```

See [Keys Mapping](keys.md) for transcribing `source-files/` credentials.

## techniques

```json
"techniques": {
  "large_payload_bytes": 50000,
  "covert_field": { "enabled": true, "field": "app.version", "marker": "SIMULATED_C2_MARKER" }
}
```

- `large_payload_bytes` — size of the blob the `large` technique attaches.
- `covert_field.field` — which telemetry field the `covert` technique hides data
  in (e.g. `ai.application.ver` for App Insights).
- `covert_field.marker` — the plaintext hidden (base64-encoded) inside that field.

## middleware

An ordered list of enabled request/response plugins. See [Middleware](middleware.md).

```json
"middleware": [
  { "name": "allowlist",       "options": { "hosts": ["your-host.com"] } },
  { "name": "extra_headers",   "options": { "headers": { "Authorization": "Bearer TEST" } } },
  { "name": "tag_correlation", "options": { "header": "X-Run", "value": "run-42" } },
  { "name": "retry_on_status", "options": { "statuses": [429, 503], "max": 2 } }
]
```

## transcript

```json
"transcript": { "redact": ["ikey", "apikey", "authorization", "security_token"] }
```

`redact` — keys masked (case-insensitive) in any exported transcript, so secrets
stay out of saved files.
