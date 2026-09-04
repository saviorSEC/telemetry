# LinkedIn Security — initial disclosure (2026-07-12)

**Researcher:** ek0ms savi0r · routed to security@linkedin.com

## Finding summary (as reported)
Unauthenticated telemetry injection across LinkedIn advertising infrastructure:
3 subdomains (`px.ads.linkedin.com`, `dc.ads.linkedin.com`, `ads.linkedin.com`), 39+
endpoints tested, HTTP 200 with unique event IDs.

Evidence headers observed: `linkedin-action: 1`, `x-li-uuid` (unique event ID),
`x-li-fabric` (prod environment markers), `Set-Cookie` (bcookie/lidc).

Payload classes submitted as data strings: XSS canaries (script/img onerror/svg
onload/iframe javascript), conversion/event/analytics/beacon/ping/log/metrics/v2 paths.

## Site representation note
As-reported severity table (Conversion Fraud / Stored XSS / Data Poisoning / Resource
Exhaustion / Attribution Corruption) is the researcher's triage framing at disclosure
time. In line with the whitepaper claim boundaries, this site states ingestion
acceptance as confirmed and treats stored-XSS / ML-poisoning / downstream-impact claims
as requiring LinkedIn-side confirmation unless separately evidenced.

## Disposition
Submitted to LinkedIn Security per correspondence; no further public disposition
received as of site build date.
