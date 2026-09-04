# Flock Safety PSIRT — follow-up correspondence (reference teal-lynx)

**Date:** 2026 (post initial disclosure) · **Researcher:** ek0ms savi0r
**Note:** live credentials redacted from this public record ([REDACTED]).

## Part 1 — Extended Segment findings

Unauthenticated events accepted by `api.segment.io/v1/track` under the client-exposed
write key ([REDACTED — provided to vendor]). All tests returned `{"success": true}` /
HTTP 200:
- XSS payload vectors (5), SQL/command-injection/path-traversal/null-byte/control-char
  payloads, XML/HTML, nested JSON (5 levels), combined payload, bulk 10/10.
- These were submitted as *data strings*; acceptance does not demonstrate execution or
  rendering. Downstream render/execution requires Flock-side confirmation (whitepaper
  claim boundary: parsed text ≠ execution).

## Part 2 — Datadog RUM (new finding)

Flock Safety uses Datadog RUM with client tokens found in public JS bundles
(`devices_main_bundle.js`, `camera_manager_bundle.js`). Client tokens are public by
design in the RUM model (same class as App Insights iKeys).
- `https://rum.browser-intake-datadoghq.com/api/v2/rum` — HTTP 202 accepted for basic
  RUM events, custom action names, HTML markers; bulk 10/10.
- Same class: client-side token, unauthenticated ingestion, provenance question
  downstream.

## Questions to Flock PSIRT (CERT/CC coordination context, planned 2026-09-05)
1–10: were synthetic records located; discarded/quarantined/retained/aggregated;
untrusted-provenance classification; can external sender modify/suppress it; survives
transformation/aggregation/export; prevented from analytics/alerting/ML; technically
distinguishable; filtering stage; trace vs intended-design basis; teal-lynx
classification (vulnerability / intended behavior / non-security).

## Disposition
Awaiting Flock PSIRT reproduction + security-impact analysis per correspondence.
