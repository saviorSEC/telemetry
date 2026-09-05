# Post-Disclosure Re-Verification Sweep — 2026-09-05 (disclosure date)

> Method: ONE benign synthetic canary per endpoint (`CoM-Sweep-20260905-1788577420`).
> No bulk, no payload strings (no XSS/SQL/cmd), no auth, no redirect-following.
> Claim boundary: an acceptance response proves ingestion-boundary receipt only —
> not retention, trusted use, or downstream impact. 43 probes, 2026-09-05 UTC.

## Still accepting unauthenticated events (open)

| Endpoint | HTTP | Signal |
|---|---|---|
| OneCollector `browser.events.data.microsoft.com/OneCollector/1.0/` (2 keys) | 204 | accepted — **note: changed from 401 on 09-04 back to 204** |
| OneCollector `vortex.data.microsoft.com/OneCollector/1.0/` (2 keys) | 204 | accepted |
| Google `android.googleapis.com/checkin` | 200 | `stats_ok:true` |
| Apple `metrics.icloud.com/metrics` | 200 | empty body |
| Meta `www.facebook.com/tr` (pixel) | 200 | pixel accepted |
| LinkedIn `px.ads.linkedin.com/collect`, `dc.ads.linkedin.com/collect` | 200 | tracking GIF |
| Baidu `hm.baidu.com/hm.gif` + `nsclick t/u/v.gif` | 200 | tracking GIF |
| CNZZ `cnzz.mmstat.com` + `s9/s4/s19 z_stat.php` | 200 | tracking GIF/empty |
| Tencent `h.trace.qq.com/kv` | 200 | accepted |
| Segment `api.segment.io/v1/track` (Flock write key) | 200 | `{"success": true}` |
| Datadog RUM `rum.browser-intake-datadoghq.com/api/v2/rum` | 202 | `{}` |

## Changed / no longer accepting as before

| Endpoint | Now | vs. original evidence |
|---|---|---|
| App Insights `eastus-8 /v2.1/track` + CarMax `dc.services /v2/track` | 200 but **`itemsReceived:0, itemsAccepted:0`** | changed — was `itemsAccepted:1` (Jun–Sep 04); envelope now rejected before accept |
| Meta `/log`, `/metrics` | 302 | was 200 in July — now redirects |
| Apple `gateway.icloud.com/metrics|telemetry` | 400 | not accepting this shape |
| Apple `diagnostics.apple.com/telemetry` | 302 | redirect |
| Apple `xp.apple.com/metrics`, `init-p01md.apple.com/telemetry` | 404 | gone/renamed |
| Google `play.googleapis.com/log` | 400 | not accepting this shape |
| Amplitude `api2.amplitude.com/2/httpapi` | 400 | **API key invalid** (rotated/revoked — good) |
| Flock first-party `analytics.flocksafety.com/*` | 403 | blocked |
| Amazon `device-metrics-us.amazon.com/DeviceMetrics` | 200 UnknownOperation | reachable, wrong format (inconclusive) |
| Tencent `pingtas.qq.com/*` | 503 | unavailable; `beacon.qq.com/beacon.gif` 404 |

## Reading (claim-bounded)

1. **OneCollector reversal:** 09-04 returned 401 `InvalidTenantToken`; 09-05 same
   endpoints return **204** for `client-id=NO_AUTH` events. Either tenant-token
   validation is not enforced on this path, or the accepted handshake differs —
   recorded as an open question, not an overclaim.
2. **App Insights delta:** endpoint still answers 200 but now reports
   `itemsAccepted:0` for the previously-accepted envelope shape. Possible added
   validation — cannot claim injection is still accepted without a matching
   accepted envelope.
3. **Pixel/analytics class (Meta/LinkedIn/Baidu/CNZZ/Tencent kv):** still return
   acceptance responses to unauthenticated events as of disclosure date.
4. Re-verification is a point-in-time observation; endpoints may change without
   notice. Raw probe log: sweep JSON in /tmp (not committed — contains client
   tokens).
