Monday, July 13, 2026 at 5:37 PM
Our reply
Hi,
Thank you for reaching out! We've received your report. Your report number is 122104644987389843. Please give us reasonable time to review this submission before disclosing any information about this report. Meta reserves the right to publish your report. For additional information, including the scope, common false positives, and conditions for closing reports as invalid, visit our website: https://bugbounty.meta.com/
Note that if you're writing to us in a language other than English, we'll only be able to respond in English at this time.
Thanks,
Meta Security
Monday, July 13, 2026 at 5:37 PM
What you submitted
Title
Unauthenticated Telemetry Event Spoofing via Caller-Supplied Meta Pixel Identifier
Description/Impact
## Summary

Meta’s production Pixel collection endpoint accepts attacker-controlled telemetry events without requiring proof that the submitting party owns or is authorized to submit events for the supplied Pixel or dataset identifier.

**Affected endpoint:**

`https://www.facebook.com/tr`

An unauthenticated external party can supply:

* A Pixel or dataset identifier
* An event name
* Destination-page information
* Referrer information
* Custom event properties
* Timestamps and other event metadata

The request does not require:

* A Facebook account
* An advertiser or Business Manager session
* An OAuth token
* A Conversions API access token
* A signed request
* An authorization header
* Proof that the sender controls the supplied telemetry identifier

Meta’s production collector processes the requests and returns `HTTP 200 OK` without an authentication or authorization challenge.

This report is narrowly focused on the failure to verify telemetry-event provenance. It is not based merely on the fact that Meta Pixel is publicly accessible from browser JavaScript.

The security concern is that an unauthenticated third party can submit fabricated telemetry under a caller-supplied Pixel or dataset identity that the third party does not control.

## Relationship to Previous Report

This report is related to Meta report:

`122102502879389843`

The earlier report included several additional endpoints and possible downstream consequences. This new submission intentionally isolates the clearest reproducible security-boundary issue affecting the Meta Pixel collection infrastructure.

## Weakness Classification

**Primary weakness:**

* CWE-360 — Trust of System Event Data

**Related weaknesses:**

* CWE-287 — Improper Authentication
* CWE-349 — Acceptance of Extraneous Untrusted Data With Trusted Data
* CWE-345 — Insufficient Verification of Data Authenticity

## Steps to Reproduce

### Step 1: Save the attached proof-of-concept script

The attached script is named:

`meta_canary.py`

The script requires the exact tested Pixel or dataset identifier as a command-line argument. It will refuse to execute when supplied with a placeholder.

### Step 2: Run the proof of concept

```bash
python3 meta_canary.py --pixel-id EXACT_TESTED_IDENTIFIER
```

No Facebook authentication, advertiser session, OAuth token, Conversions API token, signed request, or authorization header is provided.

### Step 3: Observe the destination-page field test

The script submits a harmless unique canary through the `dl` parameter:

```text
dl=https://example.com/META-CANARY-DL-[TIMESTAMP]-[NONCE]-ek0ms
```

Example request structure:

```http
GET /tr?id=EXACT_TESTED_IDENTIFIER
&ev=SecurityResearchCanary
&dl=https://example.com/META-CANARY-DL-[TIMESTAMP]-[NONCE]-ek0ms
&ts=[TIMESTAMP]
```

The collector returns:

```http
HTTP/2 200
Content-Type: text/plain
Content-Length: 0
```

No authentication or authorization error is returned.

### Step 4: Observe the referrer field test

The script submits a separate unique canary through the `rl` parameter:

```text
rl=https://example.org/META-CANARY-REFERRER-[TIMESTAMP]-[NONCE]-ek0ms
```

The collector again returns `HTTP 200` without requiring authentication or proof that the sender controls the supplied identifier.

### Step 5: Observe the custom-data field test

The script submits a third unique canary through:

```text
cd[security_research_canary]=META-CANARY-CUSTOM-[TIMESTAMP]-[NONCE]-ek0ms
```

The collector again returns `HTTP 200`.

### Step 6: Review the generated evidence file

The proof of concept automatically saves a timestamped JSON evidence file containing:

* The exact tested Pixel or dataset identifier
* The exact canary submitted in each field
* The UTC submission time
* The full request URL
* The request method
* Confirmation that no authentication was supplied
* The HTTP response code
* The response content type
* The response length
* The returned response headers

The terminal output, JSON evidence, and screenshots are attached to this report.

## Proof-of-Concept Script

```python
#!/usr/bin/env python3
"""
Meta Pixel - Unauthenticated Telemetry Canary Test

Submits three harmless unique markers through caller-controlled telemetry
fields. The script requires the exact Pixel or dataset identifier and
refuses to execute if a placeholder is supplied.

No JavaScript, callback server, data extraction, downstream access, or
denial-of-service testing is performed.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://www.facebook.com/tr"


def utc_timestamp() -> str:
return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def generate_canary(field: str) -> str:
return (
f"META-CANARY-{field}-{utc_timestamp()}-"
f"{secrets.token_hex(4)}-ek0ms"
)


def parse_arguments() -> argparse.Namespace:
parser = argparse.ArgumentParser(
description=(
"Submit harmless unauthenticated telemetry canaries "
"to the Meta Pixel collector."
)
)

parser.add_argument(
"--pixel-id",
required=True,
help="Exact Pixel or dataset identifier being tested.",
)

parser.add_argument(
"--output",
help="Optional JSON evidence filename.",
)

return parser.parse_args()


def validate_identifier(identifier: str) -> str:
cleaned = identifier.strip()

if not cleaned:
raise ValueError("The identifier cannot be empty.")

placeholders = {
"REPLACE_WITH_EXACT_TESTED_IDENTIFIER",
"[TESTED_IDENTIFIER]",
"TESTED_IDENTIFIER",
"EXACT_TESTED_IDENTIFIER",
"PIXEL_ID",
}

if cleaned in placeholders:
raise ValueError(
"A placeholder was supplied. Use the exact tested identifier."
)

return cleaned


def submit_test(
tested_identifier: str,
field_name: str,
field_params: dict[str, str],
) -> dict[str, Any]:
canary = next(
value
for value in field_params.values()
if "META-CANARY-" in value
)

params = {
"id": tested_identifier,
"ev": "SecurityResearchCanary",
"ts": str(int(time.time() * 1000)),
**field_params,
}

submitted_at = datetime.now(timezone.utc).isoformat()

response = requests.get(
ENDPOINT,
params=params,
headers={
"User-Agent": "Security-Research-Canary/1.0",
"Accept": "*/*",
},
timeout=15,
allow_redirects=False,
)

result = {
"field_tested": field_name,
"canary": canary,
"submitted_at_utc": submitted_at,
"tested_identifier": tested_identifier,
"authentication_supplied": False,
"request_method": "GET",
"request_url": response.request.url,
"status_code": response.status_code,
"content_type": response.headers.get("content-type"),
"response_length": len(response.content),
"response_headers": dict(response.headers),
}

print(f"Field tested: {field_name}")
print(f"Canary: {canary}")
print(f"UTC time: {submitted_at}")
print(f"Tested identifier: {tested_identifier}")
print("Authentication supplied: No")
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Response length: {len(response.content)}")
print(f"Request URL: {response.request.url}")
print("-" * 78)

return result


def main() -> int:
args = parse_arguments()

try:
tested_identifier = validate_identifier(args.pixel_id)
except ValueError as error:
print(f"Error: {error}", file=sys.stderr)
return 1

dl_canary = generate_canary("DL")
referrer_canary = generate_canary("REFERRER")
custom_canary = generate_canary("CUSTOM")

tests = [
(
"dl",
{"dl": f"https://example.com/{dl_canary}"},
),
(
"rl",
{"rl": f"https://example.org/{referrer_canary}"},
),
(
"custom_data",
{
"cd[security_research_canary]": custom_canary,
},
),
]

evidence: dict[str, Any] = {
"researcher": "ek0ms",
"endpoint": ENDPOINT,
"test_started_utc": datetime.now(timezone.utc).isoformat(),
"tested_identifier": tested_identifier,
"authentication_supplied": False,
"tests": [],
}

for field_name, field_params in tests:
try:
result = submit_test(
tested_identifier=tested_identifier,
field_name=field_name,
field_params=field_params,
)
evidence["tests"].append(result)
except requests.RequestException as error:
evidence["tests"].append(
{
"field_tested": field_name,
"error": str(error),
}
)
print(
f"Request failed for {field_name}: {error}",
file=sys.stderr,
)

time.sleep(1)

evidence["test_completed_utc"] = (
datetime.now(timezone.utc).isoformat()
)

output_path = (
Path(args.output)
if args.output
else Path(f"meta_canary_evidence_{utc_timestamp()}.json")
)

output_path.write_text(
json.dumps(evidence, indent=2),
encoding="utf-8",
)

print(f"Evidence saved to: {output_path.resolve()}")

return 0


if __name__ == "__main__":
raise SystemExit(main())
```

## Actual Result

Meta’s production Pixel collector accepts and processes telemetry requests containing:

* A caller-supplied Pixel or dataset identifier
* A caller-supplied event name
* Caller-controlled page and referrer values
* Caller-controlled custom event properties
* Caller-controlled timestamps

The requests receive `HTTP 200` without any proof that the submitting party owns or controls the represented telemetry identifier.

## Expected Result

Meta should prevent an unauthenticated third party from submitting events that are attributed to a Pixel, dataset, advertiser, application, or analytics source they do not control.

Because browser-based Pixel collection may need to remain publicly accessible, Meta should at minimum ensure that:

1. The supplied identifier is valid for the request context.
2. Events cannot be attributed to an unrelated advertiser or dataset without additional authorization or verification.
3. Anonymous browser events retain an immutable provenance and trust classification.
4. Anonymous events remain distinguishable from authenticated server-side events.
5. Low-trust telemetry cannot influence protected attribution, fraud, security, audience, or automated decision systems without additional validation.

## Security Concern

The vulnerability exists at the telemetry-ingestion trust boundary.

If unauthenticated submissions are associated with valid telemetry objects without reliable producer verification or downstream trust separation, an attacker may be able to fabricate events including:

* Page views
* Leads
* Registrations
* Purchases
* Custom conversion events
* Landing-page activity
* Referrer activity
* Custom behavioral signals

Potential downstream consequences include:

* Corruption of advertising measurement
* False conversion attribution
* Distortion of campaign-performance reporting
* Pollution of audience or behavioral datasets
* False signals entering fraud and abuse-analysis systems
* Reduced confidence in advertiser-facing analytics
* Attacker-controlled telemetry reaching reports, exports, or secondary processors

Meta controls the private downstream pipeline and must determine the exact handling and impact of the submitted canaries.

## Requested Internal Validation

Please trace the canaries and timestamps included in the attached evidence and determine:

1. Whether each request was discarded, sampled, quarantined, normalized, or stored;
2. Whether the supplied identifier mapped to a valid Meta Pixel, dataset, advertiser, application, or internal telemetry object;
3. Whether the submitted events were attributed to that object;
4. Whether the records retained an immutable unauthenticated provenance classification;
5. Whether they entered the same reporting or processing environment as authorized events;
6. Whether they were eligible to influence attribution, reporting, audiences, fraud detection, analytics, or automated systems; and
7. Whether caller-controlled properties could reach dashboards, exports, or other downstream processors.

Security Concern

The vulnerability exists at the telemetry-ingestion trust boundary.

If unauthenticated submissions are associated with valid telemetry objects without reliable producer verification or downstream trust separation, an attacker may be able to fabricate events including:

* Page views
* Leads
* Registrations
* Purchases
* Custom conversion events
* Landing-page activity
* Referrer activity
* Custom behavioral signals

Potential downstream consequences include:

* Corruption of advertising measurement
* False conversion attribution
* Distortion of campaign-performance reporting
* Pollution of audience or behavioral datasets
* False signals entering fraud and abuse-analysis systems
* Reduced confidence in advertiser-facing analytics
* Attacker-controlled telemetry reaching reports, exports, or secondary processors

Meta controls the private downstream pipeline and must determine the exact handling and impact of the submitted canaries.
Repro Steps
**Users:**
N/A. No Meta, Facebook, advertiser, developer, or Business Manager account is required.

**Environment:**
Public production endpoint:

`https://www.facebook.com/tr`

Testing is performed from an unauthenticated external network connection using the attached Python proof of concept.

Local setup requirements:

1. Python 3 installed.
2. The Python `requests` package installed:

```bash
python3 -m pip install requests
```

3. Save the attached script as:

```text
meta_canary.py
```

4. Run the script with the exact Pixel or dataset identifier used for testing:

```bash
python3 meta_canary.py --pixel-id EXACT_TESTED_IDENTIFIER
```

No Facebook session cookie, advertiser account, OAuth token, Conversions API access token, signed request, authorization header, or other Meta credential should be configured.

**Browser:**
N/A. Reproduction uses Python `requests` from the command line and does not require a browser.

**OS:**
Linux. The proof of concept is platform-independent and should also run on Windows or macOS with Python 3 and the `requests` package installed.

1. Save the attached proof-of-concept script as:

```text
meta_canary.py
```

2. Install the required Python dependency:

```bash
python3 -m pip install requests
```

3. Run the script using the exact Meta Pixel or dataset identifier tested in this report:

```bash
python3 meta_canary.py --pixel-id EXACT_TESTED_IDENTIFIER
```


Replace `EXACT_TESTED_IDENTIFIER` with the tested identifier. The script rejects placeholder values.

4. The script sends three separate unauthenticated requests to:

```text
https://www.facebook.com/tr
```

The requests contain harmless, uniquely identifiable canaries in the following caller-controlled telemetry fields:

* Destination URL: `dl`
* Referrer URL: `rl`
* Custom event data: `cd[security_research_canary]`

Each request also contains:

```text
ev=SecurityResearchCanary
id=EXACT_TESTED_IDENTIFIER
ts=CURRENT_TIMESTAMP
```

5. Confirm that no Meta credentials are supplied. The requests do not include:

* A Facebook account session
* An advertiser or Business Manager session
* An OAuth token
* A Conversions API access token
* A signed request
* An `Authorization` header
* Proof that the sender controls the supplied Pixel or dataset identifier

6. Observe the terminal output for each request.

Example:

```text
Field tested: dl
Canary: META-CANARY-DL-[UTC-TIMESTAMP]-[NONCE]-ek0ms
Authentication supplied: No
Status: 200
Content-Type: text/plain
Response length: 0
Request URL: https://www.facebook.com/tr?id=...
```

The same result is produced for the `rl` and custom-data canaries.

7. Confirm the actual result:

* Meta’s production Pixel endpoint returns `HTTP 200`.
* No authentication or authorization challenge is returned.
* The caller controls the supplied Pixel or dataset identifier.
* The caller controls the submitted event name, URL, referrer, custom data, and timestamp.

8. Review the JSON evidence file automatically created by the script:

```text
meta_canary_evidence_[UTC_TIMESTAMP].json
```

The evidence file contains:

* The exact tested identifier
* Each unique canary value
* UTC submission timestamps
* Full request URLs
* Confirmation that no authentication was supplied
* HTTP status codes
* Response content types and lengths
* Response headers

9. Meta should trace the exact canary values internally to determine whether the events were discarded, isolated, normalized, stored, attributed to the supplied identifier, or processed by downstream reporting and analytics systems.

**Expected behavior:** Meta should prevent an unauthenticated third party from submitting events attributed to a Pixel or dataset they do not control, or permanently classify and isolate such events as unauthenticated and untrusted.

**Actual behavior:** The production collector handles caller-controlled telemetry submitted under the supplied identifier and returns `HTTP 200` without requiring proof that the sender owns or controls that telemetry source. 

Today at 5:32 AM
Our reply
Hi,
Thank you for taking the time to submit this report to our bug bounty program, we genuinely appreciate your effort in helping keep our platforms, and the people that use them, secure.
After reviewing your submission, we've determined that the reported issue does not qualify as a valid vulnerability under the scope of our bug bounty program. This may be because the behavior described is working as intended, falls outside our program scope or does not demonstrate a clear security or privacy impact. Due to the volume of reports we currently receive, we are unable to provide detailed information as to how we reached this decision.
We understand this may not be the outcome you were hoping for. If you believe this decision is incorrect or if you have additional information that demonstrates security or privacy impact we may have missed, please don't hesitate to reply to this report. We're happy to take another look.
Thank you again for participating in our program. We encourage you to continue researching and submitting any potential findings in the future.
Best regards,
Meta Bug Bounty


Review Requested  · Today at 11:10 AM
You replied
Meta Bug Bounty Team,
I am formally requesting a re-review of my reports concerning unauthenticated telemetry event submission through caller-supplied Meta application, Pixel, or dataset identifiers.
The prior closure did not address the technical issue presented. It provided a generic conclusion that the behavior may be intended, out of scope, or lacking demonstrated impact, without answering the specific provenance, attribution, storage, or downstream-processing questions raised in the report.
I respectfully request that this matter be reopened and reviewed by a product-security engineer with access to the relevant telemetry ingestion and downstream processing systems.
The finding is not merely that Meta operates a public browser telemetry endpoint. I understand that Meta Pixel is intentionally designed to receive client-side events.
The unresolved security issue is that an unauthenticated external party can submit attacker-controlled, protocol-valid events using identifiers associated with telemetry resources that the submitting party does not own or control, without providing proof of authorization for those identifiers.
I have reproduced this behavior using seven separate identifiers. I can provide the identifiers, exact canary values, timestamps, requests, responses, and related evidence privately to an assigned engineer.
The fact that a collector is intentionally public does not resolve the security question. It makes the following controls essential:
1. Whether events submitted under valid identifiers are attributed to those applications, Pixels, or datasets;
2. Whether fabricated events are stored or made visible in advertiser or application reporting;
3. Whether an immutable provenance marker distinguishes unauthenticated browser input from authenticated or otherwise verified events;
4. Whether that distinction survives aggregation, transformation, deduplication, export, and downstream processing;
5. Whether unauthenticated events can influence attribution, audiences, measurement, billing, experimentation, abuse detection, fraud systems, automated decision-making, or machine-learning workflows;
6. Whether Meta attaches cookies, timestamps, account context, device context, or other metadata that may cause the fabricated event to be treated as legitimate user activity; and
7. Whether invalid or unauthorized identifiers are rejected internally, even where the public endpoint initially returns an accepting HTTP response.
Only Meta can answer these questions because the relevant storage and processing systems are private. I will not access another party’s reporting resources, perform sustained production injection, or attempt downstream exploitation without explicit written authorization.
That restraint must not be interpreted as an absence of impact. It reflects responsible research boundaries.
This report is part of a broader coordinated investigation into substantially similar telemetry-provenance failures across multiple unrelated technology providers. Without disclosing confidential case details, I can state that other vendors have independently escalated comparable findings to engineering teams, acknowledged the underlying trust-boundary concern, or begun evaluating and planning remediation.
The consistency of this behavior across otherwise unrelated platforms suggests that unauthenticated telemetry injection may represent an emerging cross-vendor vulnerability class rather than an isolated implementation issue.
Meta should therefore evaluate its implementation on its own technical merits now. If Meta is affected by the same provenance failure, subsequent remediation or public disclosure by other vendors will not change the underlying condition. It will only establish that the issue was reported to Meta in advance and that a substantive technical review was requested.
Data-protection and integrity implications:
Where the submitted events contain, become associated with, or influence the processing of personal data, the issue may engage the GDPR principles of accuracy and integrity and confidentiality under Articles 5(1)(d) and 5(1)(f). Article 32 also requires appropriate technical and organizational measures capable of ensuring the ongoing integrity, availability, and resilience of processing systems.
These obligations cannot be resolved solely by stating that public telemetry collection is intended. The relevant question is whether Meta has appropriate controls preventing unauthenticated, attacker-controlled input from being misattributed, trusted, or propagated into systems that rely upon the integrity of that information.
Meta’s precise legal role may vary by processing operation. Meta Platforms Ireland may act as a controller, joint controller, or processor depending on the particular data flow and relationship. I am not asserting that one classification applies universally. I am requesting that Meta’s security and privacy teams evaluate the actual processing roles and obligations applicable to this ingestion pipeline.
Requested re-review and technical validation
As part of this formal re-review, please escalate the matter to an engineer with access to the relevant ingestion and downstream systems and perform the following:
* Trace the previously supplied canary events;
* Confirm whether each event was discarded, quarantined, stored, attributed, aggregated, or exported;
* Confirm what producer-authentication or provenance classification was attached;
* Confirm whether the caller-supplied identifier was accepted as authoritative;
* Identify which downstream systems, if any, received the event;
* Confirm whether unauthenticated events can influence protected business, safety, security, advertising, or automated-decision systems; and
* Provide a vendor-controlled test asset or written testing authorization if additional verification is required.
Please do not close the report again with a generic statement that the endpoint is intended to accept browser telemetry. That statement does not answer whether an unauthenticated outsider can impersonate a legitimate telemetry producer or whether Meta preserves the untrusted origin of that data throughout its lifecycle.
Depending on Meta’s internal handling, the impact could range from properly isolated low-trust collection to material corruption of analytics, attribution, security signals, advertiser data, or automated systems.
I am not presenting every downstream consequence as already proven. I am explicitly requesting that Meta validate those consequences using the internal access available only to Meta.
This communication constitutes documented notice of the unresolved condition and a formal request for re-review.
Please confirm one of the following:
1. The report has been reopened and assigned for engineering re-review;
2. The previously submitted canaries have been traced and the relevant findings can be shared;
3. Meta has determined, following substantive engineering review, that the events are discarded or permanently isolated from trusted downstream systems; or
4. Meta is declining to perform the requested technical review.
Please also confirm whether this matter has been reviewed by both the relevant product-security engineering team and the appropriate privacy or data-protection personnel.
Regards,
Kelly
Independent Security Researcher
