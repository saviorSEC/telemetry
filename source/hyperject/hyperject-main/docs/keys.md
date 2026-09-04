# Keys Mapping (source-files → config)

[← Docs home](README.md)

The only stored credentials in `source-files/` are in `hyperject-msrc.py`
(App Insights iKeys and OneCollector keys). This page shows how those structures
map to `config.json`. **hyperject ships no real key values** — put your own
authorized values in place of the placeholders.

## App Insights iKeys

The source keeps a list of iKeys, each annotated with the product it belongs to:

```python
# source-files/hyperject-msrc.py
AI_IKEYS = [
    "....",   # Power BI WFE
    "....",   # TriShell
    "....",   # Fabric Main App (Global)
    "....",   # Fabric TriShell
]
AI_ENDPOINTS = ["eastus-0.in.applicationinsights.azure.com", "eastus-8...."]
```

In config, the endpoints become full URLs and each iKey becomes an annotated
entry (the comment becomes a `label` that shows in results). Every
`endpoint × iKey` is probed.

```json
"app_insights": {
  "enabled": true,
  "endpoints": [
    "https://<your-endpoint-1>/v2.1/track",
    "https://<your-endpoint-2>/v2.1/track"
  ],
  "ikeys": [
    { "ikey": "REPLACE_WITH_YOUR_IKEY_1", "label": "Power BI WFE" },
    { "ikey": "REPLACE_WITH_YOUR_IKEY_2", "label": "TriShell" },
    { "ikey": "REPLACE_WITH_YOUR_IKEY_3", "label": "Fabric Main App" },
    { "ikey": "REPLACE_WITH_YOUR_IKEY_4", "label": "Fabric TriShell" }
  ],
  "accept_field": "itemsAccepted"
}
```

> A bare GUID string also works (`"ikeys": ["<guid>"]`); the annotated object just
> carries the label through to the result rows.

## OneCollector keys

The source stores objects with `key`, `ikey`, and `origin`:

```python
OC_KEYS = [
  { "key": "<composite>", "ikey": "<ikey>", "origin": "login.microsoftonline.com (Azure AD)" },
  { "key": "<composite>", "ikey": "<ikey>", "origin": "portal.azure.com (Azure Portal)" },
]
OC_ENDPOINTS = ["browser.events.data.microsoft.com", "vortex....", ... ]  # 9
```

This shape is supported **verbatim** — copy it straight in. The module reads
`key` (the `apikey` query param), `ikey` (sent as `iKey: o:<ikey>`), and derives
the browser `Origin`/`Referer` from `origin` (matching the source's
`"portal" in origin` / `"login" in origin` logic). Every `endpoint × key` is
probed.

```json
"one_collector": {
  "enabled": true,
  "endpoints": [
    "https://<your-endpoint-1>/OneCollector/1.0/",
    "https://<your-endpoint-2>/OneCollector/1.0/"
  ],
  "keys": [
    { "key": "REPLACE_WITH_YOUR_KEY_1", "ikey": "REPLACE_WITH_YOUR_IKEY_1",
      "origin": "login.microsoftonline.com (Azure AD)" },
    { "key": "REPLACE_WITH_YOUR_KEY_2", "ikey": "REPLACE_WITH_YOUR_IKEY_2",
      "origin": "portal.azure.com (Azure Portal)" }
  ],
  "accept_status": 204
}
```

Set `origin_url` on a key to spoof a specific Origin/Referer explicitly; add
`label` to override how the key appears in results.

## Other source files

`hyperject-goog.py`, `test_service_trace.py`, `test_program_analytics.py`,
`test_platform_metrics.py`, and `test_software_pixel.py` use **no stored
credentials** — they probe unauthenticated ingest. Their targets are plain
`endpoint` / `base_url` fields (see [Configuration](configuration.md) and
[Modules](modules.md)).

## Validation

After transcribing keys, run:

```bash
hyperject validate -c config.json
```

Validation looks inside annotated iKey objects too, so any remaining `REPLACE_`
placeholder — bare or nested — is caught before you can run.
