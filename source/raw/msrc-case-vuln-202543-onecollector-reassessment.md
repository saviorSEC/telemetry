# MSRC Case — VULN-202543 — OneCollector NO_AUTH Telemetry Provenance Failure (Reassessment)

**Status:** Complete-NA — closed as a non-MSRC case (2026-07-17)
**Security impact:** Tampering · **Component:** OneCollector / 1DS telemetry ingestion
**External tracking ID:** COM-UTI-1DS-2026 · **Reported:** 2026-07-17

---

## Submission summary

Requested reassessment of MSRC Case 125992 / VULN-200045 based on Microsoft's closure
explanation. Accepted: the client-side iKey is a routing identifier, not a credential;
public collectors may legitimately accept events from clients that cannot authenticate at
ingestion. The unresolved issue:

> Whether events received through `client-id=NO_AUTH` remain durably identified as
> unverified and are technically prevented from entering any context where Microsoft
> relies on telemetry authenticity, integrity, accuracy, or producer identity.

## Confirmed behavior (as reported)

Production endpoints accept internet-originated telemetry with `client-id=NO_AUTH`:

- `https://browser.events.data.microsoft.com/OneCollector/1.0/`
- `https://vortex.data.microsoft.com/OneCollector/1.0/`

Harmless, uniquely tagged canary events submitted without OAuth token, Microsoft account,
client certificate, request signature, device attestation, or proof of producer control.
Endpoints returned HTTP 204 No Content. Caller-controlled: event name, timestamp,
application-version-like values, custom properties, unique research canary
(`MSRC-125992-REASSESSMENT-20260717T162204Z-AB0A7F36B40F`).

Acknowledged in the submission: HTTP 204 alone does not prove storage, attribution,
visibility, downstream influence, ML use, or execution — those require Microsoft-side
tracing.

## Basis for reassessment

Microsoft's closure confirmed fabricated telemetry injection is a known condition and that
the security conclusion depends on backend cleaning. Backend cleaning and provenance
preservation are what distinguish safe low-trust ingestion from a telemetry-integrity
failure. Ten security guarantees were listed for validation (explicit unverified
classification; durability through transformation/aggregation/export; iKey routing-only;
no replacement of authoritative identity data; cleaning before integrity-sensitive
consumers; technical segregation; no equivalence with authenticated telemetry; no
association with legitimate resources without verification; no material aggregate
distortion pre-cleaning; canary disposition).

Classification proposed: CWE-360 (Trust of System Event Data), CWE-345 (Insufficient
Verification of Data Authenticity), CWE-349 (Acceptance of Extraneous Untrusted Data With
Trusted Data). No reward requested. Context: broader cross-vendor investigation;
publication planned following coordinated disclosure; Microsoft's position represented
accurately.

## Additional evidence provided

While completing a Microsoft Customer Voice survey (customervoice.microsoft.com), the
first-party application was observed submitting live telemetry to
`browser.events.data.microsoft.com/OneCollector/1.0/` — first-party traffic to the same
NO_AUTH surface under test.

## MSRC disposition

- 2026-07-17: VULN-202543 closed as a **non-MSRC case**, status Complete-NA, without a
  substantive explanation in the activity feed.
- Researcher requested clarification of disposition + appropriate Microsoft owner;
  MSRC email response directed the requester to contact the case manager of the original
  case for reassessment.
- No canary trace or provenance-guarantee confirmation was provided before closure.

## Site representation note

Represented as: reassessment filed; closed Complete-NA (non-MSRC); provenance questions
unanswered in the record. Consistent with whitepaper claim boundaries — ingestion
acceptance confirmed externally; downstream disposition not independently verifiable.
