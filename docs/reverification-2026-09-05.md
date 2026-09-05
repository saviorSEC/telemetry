# Post-Disclosure Re-Verification Sweep — 2026-09-05 (disclosure date)

> Method: ONE benign synthetic canary per endpoint (canary `CoM-Sweep-20260905-1788577420`,
> plus `CoM-Retest-20260905` for App Insights). No bulk, no payload strings (no
> XSS/SQL/cmd), no auth, no redirect-following on acceptance checks.
> Claim boundary: an acceptance response proves ingestion-boundary receipt only — not
> retention, trusted use, or downstream impact. 43 probes + 6-key retest, 2026-09-05 UTC.

## Correction to the 09-04 note (important)

The 09-04 check recorded OneCollector as "401 InvalidTenantToken — behavior changed".
That was a **test artifact**: the probe script used truncated/masked keys. Re-tested
2026-09-05 with the full keys from the research record — OneCollector returns
**204 No Content for `client-id=NO_AUTH` events on both endpoints**. No fix observed.

## Still accepting unauthenticated events (open)

| Endpoint | HTTP | Signal |
|---|---|---|
| OneCollector `browser.events.data.microsoft.com/OneCollector/1.0/` (2 keys) | **204** | accepted — no fix |
| OneCollector `vortex.data.microsoft.com/OneCollector/1.0/` (2 keys) | **204** | accepted — no fix |
| App Insights `eastus-8.in.applicationinsights.azure.com/v2.1/track` (4 Power BI/Fabric keys) | **200** | `itemsAccepted:1` — no fix |
| App Insights `dc.services.visualstudio.com/v2/track` (CarMax key 78f195a3) | **200** | `itemsAccepted:1` — no fix |
| Google `android.googleapis.com/checkin` | **200** | `stats_ok:true` |
| Apple `metrics.icloud.com/metrics` | **200** | accepted |
| Meta `www.facebook.com/tr` (pixel) | **200** | pixel accepted |
| LinkedIn `px.ads.linkedin.com/collect`, `dc.ads.linkedin.com/collect` | **200** | tracking GIF |
| Baidu `hm.baidu.com/hm.gif` + `nsclick t/u/v.gif` | **200** | tracking GIF |
| CNZZ `cnzz.mmstat.com` + `s9/s4/s19 z_stat.php` | **200** | tracking GIF / empty |
| Tencent `h.trace.qq.com/kv` | **200** | accepted |
| Segment `api.segment.io/v1/track` (Flock write key) | **200** | `{"success": true}` |
| Datadog RUM `rum.browser-intake-datadoghq.com/api/v2/rum` | **202** | `{}` |

## Partially changed / remediated

| Endpoint | Now | Reading |
|---|---|---|
| App Insights CarMax key `8384dafb…` | 400 `Invalid instrumentation key` | **key revoked/rotated** — partial CarMax-side remediation (sibling key `78f195a3…` still accepts) |
| Amplitude `api2.amplitude.com/2/httpapi` | 400 `Invalid API key` | key no longer valid — rotated/revoked |
| Meta `/log`, `/metrics` | 302 | redirect — no longer direct 200 |
| Apple `diagnostics.apple.com/telemetry` | 302 | redirect |

## Unchanged non-accepting / needs-format (not regressions)

- Apple `gateway.icloud.com/metrics|telemetry` 400, `xp.apple.com/metrics` 404,
  `init-p01md.apple.com/telemetry` 404, `feedbackws.apple.com` + `metrics.apple.com` conn-error
- Google `play.googleapis.com/log` 400 (shape), Amazon `DeviceMetrics` 200
  UnknownOperation (protobuf format required — consistent with NOT-VULN note)
- Tencent `pingtas.qq.com/*` 503, `beacon.qq.com/beacon.gif` 404, `report.qq.com` conn-error
- Flock first-party `analytics.flocksafety.com/*` 403

## Reading (claim-bounded)

1. **No meaningful remediation across the class as of disclosure date.** The validated
   ingestion surfaces (OneCollector, App Insights, Android Check-In, Apple iCloud
   metrics, Meta pixel, LinkedIn, Baidu, CNZZ, Tencent kv, Segment, Datadog RUM) all
   still accept unauthenticated synthetic telemetry with client-exposed keys.
2. **Two partial remediations observed:** one of two CarMax App Insights keys now
   returns `Invalid instrumentation key` (rotated), and the Amplitude key in the
   research record is no longer valid. Sibling/remaining keys still accept.
3. Point-in-time observation; endpoints may change without notice. Raw probe log kept
   out of the repo (contains client tokens).
