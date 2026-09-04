# Post-Disclosure Re-Verification — 2026-09-04

> Method: one benign synthetic canary per endpoint (no bulk, no payloads, no auth) —
> exactly the claim-boundary methodology in the whitepaper. Canary
> `CoM-Reverify-20260904-1788546528`.

| Endpoint | Case | Result 2026-09-04 | vs. original finding |
|---|---|---|---|
| `eastus-8.in.applicationinsights.azure.com/v2.1/track` | VULN-193698 | **HTTP 200 — `itemsReceived:1, itemsAccepted:1, errors:[]`** | **STILL ACCEPTING unauthenticated injection** — unchanged from June 2026 |
| `browser.events.data.microsoft.com/OneCollector/1.0/` | VULN-200045 | HTTP 401 — `{"acc":0,"rej":1,"efi":{"InvalidTenantToken":[0]}}` | **Behavior changed** — July 2026 returned 204; now rejects this payload shape with InvalidTenantToken |
| `vortex.data.microsoft.com/OneCollector/1.0/` | VULN-200045 | HTTP 401 — `{"acc":0,"rej":1,"efi":{"InvalidTenantToken":[0]}}` | **Behavior changed** — same as above |

## Reading (honest, claim-bounded)

1. **Application Insights (VULN-193698 telemetry element): still accepts unauthenticated
   synthetic events as of 2026-09-04.** MSRC closed the case citing the source-map fix
   (findings 1–3) and assessed the ingestion element as Low/by-design. The ingestion
   boundary behavior is unchanged: 200 + `itemsAccepted:1`. Retention/trust disposition
   remains Microsoft-side and unverified externally — consistent with the whitepaper.

2. **OneCollector (VULN-200045/125992, VULN-202543): behavior changed since July.** The
   July-2026 evidence showed 204 No Content for `client-id=NO_AUTH` events. The
   2026-09-04 probe now receives **401 InvalidTenantToken** for the same payload shape.
   Two candidate readings — (a) tenant-token validation was added (remediation), or
   (b) the current 1DS client handshake now supplies a tenant token this static payload
   lacks (format drift). We do not claim which. A follow-up with the current SDK's exact
   envelope shape is needed before asserting "fixed" or "still open" for OneCollector.

3. No bulk testing, no rate-limit probing, no payload-execution testing was performed on
   this pass. One request per endpoint, harmless synthetic event.

## Site representation

- App Insights row: disposition note updated with 2026-09-04 re-verification (still
  accepting).
- OneCollector row: disposition note updated to reflect the 401 change + open question.
- Master report marked "evidence as of July 2026; re-verified 2026-09-04 where noted."
