# Google VRP Correspondence — Android Check-In Telemetry Provenance

> **Editorial note (site):** This page preserves the researcher's correspondence with the
> Google Vulnerability Rewards Program regarding `android.googleapis.com/checkin`.
> The **corrected VRP report** (below) supersedes earlier drafts and explicitly limits its
> claims to the externally observable provenance boundary. Earlier follow-up language that
> asserted downstream storage, fleet impact, or payload execution was **withdrawn** from the
> formal report because those effects cannot be confirmed from outside Google — consistent
> with the claim boundaries in the [whitepaper](whitepaper.html). Vendor responses are
> reproduced for transparency; a vendor's statement is not independently verified by us.

---

## Corrected VRP report — "Unauthenticated Telemetry Injection in Android Check-In"

**Vulnerability Description**

## Unauthenticated Telemetry Injection in Android Check-In — Unverified Client-Supplied Device Data Accepted at Bootstrap

Affected endpoint:

`https://android.googleapis.com/checkin`

Related prior issue:

`533164589`

This is a corrected server-side report submitted through the Google VRP after the Android team instructed me to file a new BugHunter report if I disputed the prior disposition.

Google previously stated that unauthenticated check-ins are intentional because a new device may not yet possess credentials. Google also stated that `stats_ok: true` means the server received and parsed the request, not that the submitted data was trusted or executed.

That explanation does not resolve the vulnerability reported here.

The vulnerability is **unauthenticated telemetry injection**: an external caller can submit device-identity-like and telemetry fields without proving control of the asserted producer. The security question is what happens to those fields after parsing.

Google has relied on internal handling and segregation of unverified input as the reason this behavior is safe. I am therefore requesting evidence that the submitted event is actually marked **untrusted/unsafe** and remains that way through its lifecycle.

I am not requesting another generic statement that unauthenticated bootstrap is "working as intended." That is not responsive to the provenance issue.

I am requesting a trace result for the supplied canary and a direct answer to the following:

1. Is the event discarded immediately after parsing?
2. Is it quarantined?
3. Is it retained with an explicit, durable `untrusted`, `unauthenticated`, or equivalent safety classification?
4. Can caller-supplied `android_id`, `security_token`, or `device_info` values become associated with an existing device or account?
5. Can the event be aggregated, exported, or exposed to a consumer before verification?
6. Does the untrusted classification survive every transformation and storage stage?
7. Are downstream consumers technically prevented from treating this event as authenticated device telemetry?

Google is the only party able to inspect the private downstream system. Closing the report because an external researcher cannot observe that private system is not a technical resolution of the provenance question.

A conclusory "working as intended" response is insufficient. Please provide one of the following concrete dispositions for the submitted canary:

- **Discarded after parsing**;
- **Quarantined**;
- **Retained with an immutable untrusted/unsafe provenance marker**;
- **Verified and promoted only after a separate authoritative identity check**; or
- **Google cannot substantiate that the event remains segregated from trusted telemetry**.

I am not asking Google to disclose sensitive architecture, filtering logic, or abuse-detection thresholds. I am asking for enough evidence to support Google's own security conclusion.

### Confirmed behavior

A remote party can send a check-in request without:

- An API key;
- OAuth authentication;
- A Google account;
- A client certificate;
- Device attestation;
- A cryptographic request signature; or
- Proof that the caller controls the asserted device identity.

The request includes caller-controlled fields such as:

- `android_id`;
- `security_token`;
- `device_info`;
- Manufacturer, model, and build strings;
- Timestamps;
- Locale; and
- A unique research canary.

The server returns HTTP 200 with a response such as:

```json
{
 "stats_ok": true,
 "time_msec": "<SERVER-GENERATED-TIMESTAMP>"
}
```

This establishes receipt and parsing only.

It does not, by itself, establish persistence, attribution, trusted use, aggregation, export, execution, or impact on any specific downstream system. Those facts require Google-side tracing.

### Security boundary

Unauthenticated bootstrap may be intentional. Loss of provenance is not.

The endpoint is safe only if caller-controlled data remains explicitly untrusted until a separate authoritative verification step succeeds.

The relevant weakness classifications are:

- **CWE-360 — Trust of System Event Data**
- **CWE-345 — Insufficient Verification of Data Authenticity**
- **CWE-349 — Acceptance of Extraneous Untrusted Data With Trusted Data**

This report does not rely on prior claims involving Waymo, BigQuery, Pub/Sub, machine learning, stored injection, fleet systems, or denial of service. Those claims are not necessary to evaluate the telemetry-provenance boundary.

**Attack Preconditions**

The attacker needs only:

- Internet access;
- The ability to send one HTTPS POST request; and
- Knowledge of the public endpoint.

No account, API key, OAuth token, client certificate, physical Android device, local access, valid Android security token, or user interaction is required.

The attached PoC sends exactly one synthetic canary. It performs no retries, bulk traffic, rate-limit testing, flooding, payload-execution testing, or testing involving a real user, device, account, or third-party identifier.

**Reproduction Steps / POC**

1. Install the `requests` dependency if necessary:

```bash
python3 -m pip install requests
```

2. Review the attached file:

`google_checkin_single_canary_poc.py`

3. Run it without network activity to inspect the exact request:

```bash
python3 google_checkin_single_canary_poc.py
```

4. Send exactly one canary request:

```bash
python3 google_checkin_single_canary_poc.py --send
```

5. Record:

- The generated canary;
- HTTP status;
- Response body; and
- The generated `google_checkin_evidence_<CANARY>.json` file.

The PoC uses obvious synthetic research values and includes a unique field in `device_info`:

```text
research_canary:GOOGLE-VRP-CHECKIN-PROVENANCE-<UTC-TIMESTAMP>-<RANDOM>
```

Expected externally observable result:

```json
{
 "stats_ok": true,
 "time_msec": "<SERVER-GENERATED-TIMESTAMP>"
}
```

The PoC deliberately does not characterize that response as proof of storage or downstream trust.

### Required Google-side verification

Trace the exact canary and provide its final disposition.

For each submitted field—especially `android_id`, `security_token`, `device_info`, and `research_canary`—state whether it was:

- Ignored;
- Replaced;
- Validated;
- Discarded;
- Quarantined;
- Temporarily retained;
- Persisted with an immutable untrusted/unsafe marker;
- Associated with a device or account;
- Aggregated;
- Exported; or
- Delivered to a downstream consumer.

Also identify the enforcement point that prevents an unauthenticated event from being treated as authenticated telemetry.

### Expected secure result

The event is either discarded or retained with a durable untrusted/unsafe provenance classification that cannot be removed before authoritative device verification.

Caller-supplied identity fields cannot establish, impersonate, modify, or become associated with an existing device identity.

No consumer that requires trusted device telemetry can access or act on the event before verification.

### Actual externally observable result

The production endpoint receives and parses one unauthenticated request containing caller-controlled device-identity-like fields.

The response does not reveal whether the event is marked unsafe, discarded, segregated, or later consumed.

That missing fact is the exact reason Google must trace the supplied canary rather than close the report with a generic design explanation.

### Requested disposition

Please provide a technically specific answer:

- **The canary was discarded**;
- **The canary was quarantined**;
- **The canary was retained with an immutable untrusted/unsafe designation**;
- **The canary was promoted only after separate authoritative verification**; or
- **Google cannot confirm those controls**.

Anything less does not resolve the reported telemetry-provenance boundary.
