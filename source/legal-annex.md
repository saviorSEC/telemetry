# Telemetry Integrity: Potential Legal and Regulatory Considerations

> **Research note:** This document identifies laws, regulations, and standards that may become relevant when a system accepts unauthenticated, attacker-controlled telemetry. It does not conclude that any particular organization has violated a law. Applicability depends on whether the events are retained, associated with real people or devices, propagated downstream, used for automated decisions, or otherwise affect protected data or regulated systems.

## Questions that determine legal relevance

Before citing a law in a report, establish or ask the vendor to determine:

* Does the collector only parse the event, or is the event retained?
* Is the event associated with a real user, household, device, account, application, vehicle, or organization?
* Does the system attach cookies, IP addresses, account identifiers, timestamps, geolocation, or other personal data?
* Is the event permanently labeled as coming from an unauthenticated or unverified producer?
* Does that provenance label survive transformation, aggregation, storage, export, and reuse?
* Can the event influence analytics, advertising, billing, fraud detection, security decisions, safety operations, regulatory reporting, or machine-learning systems?
* Can a consumer inspect, correct, or delete an inaccurate record created through the telemetry pipeline?
* Is the affected organization or system subject to sector-specific rules covering health, finance, children, vehicles, critical infrastructure, or high-risk AI?

---

## European data-protection considerations

### GDPR Article 4(12): Personal-data breach definition

A GDPR “personal data breach” can include the accidental or unlawful **alteration** of personal data, not only theft or disclosure. If unauthenticated telemetry modifies or becomes incorporated into a person’s record, the integrity impact may warrant assessment under this definition. Mere acceptance of anonymous fabricated data does not by itself establish a personal-data breach.

### GDPR Article 5(1)(d): Accuracy

Personal data must be accurate and, where necessary, kept up to date. Reasonable steps must be taken to erase or rectify inaccurate personal data without delay, considering the purposes for which it is processed.

This may be relevant when fabricated telemetry becomes associated with a real user, device, account, location, vehicle, or behavioral profile.

### GDPR Article 5(1)(f): Integrity and confidentiality

Personal data must be processed with appropriate security, including protection against unauthorized or unlawful processing and accidental loss, destruction, or damage.

Unauthenticated telemetry ingestion may implicate this principle if attacker-controlled data can alter protected records or enter systems that assume the information came from a legitimate producer.

### GDPR Article 16: Right to rectification

A person has the right to obtain correction of inaccurate personal data concerning them.

This becomes especially relevant if fabricated telemetry is attached to a user profile but the organization cannot identify, explain, or correct the source of the inaccurate information.

### GDPR Article 25: Data protection by design and by default

Controllers must implement appropriate technical and organizational measures designed to implement data-protection principles effectively.

Potentially relevant controls include producer authentication, provenance labeling, segregation of unverified events, data minimization, validation, and prevention of unauthorized association with real users or devices.

### GDPR Article 32: Security of processing

Controllers and processors must implement measures appropriate to risk to ensure the ongoing confidentiality, integrity, availability, and resilience of processing systems.

A telemetry architecture that accepts unverified data is not automatically unlawful. The question is whether appropriate controls prevent that input from being mistaken for trusted data or improperly altering personal information.

### GDPR Articles 33 and 34: Breach notification

Notification duties may arise if unauthorized telemetry injection constitutes a personal-data breach and creates the relevant level of risk to individuals.

These provisions should not be cited as automatically triggered. Internal tracing is needed to determine whether protected personal data was actually altered and whether the risk thresholds were met.

---

## European cybersecurity and AI considerations

### NIS2 Directive — Article 21

For essential and important entities within NIS2’s scope, Article 21 requires appropriate and proportionate cybersecurity risk-management measures. Covered areas include risk analysis, incident handling, business continuity, supply-chain security, secure development and maintenance, vulnerability handling, assessment of control effectiveness, access control, and authentication.

A telemetry-provenance failure may be relevant where the collector supports an essential service, digital infrastructure, managed service, cloud service, or another covered operation. Applicability depends on the entity, sector, Member State implementation, and system involved.

### EU Artificial Intelligence Act — Articles 10 and 15

For covered high-risk AI systems, Article 10 addresses data governance and the quality of training, validation, and testing datasets. Article 15 addresses accuracy, robustness, and cybersecurity, including resilience against attempts by unauthorized third parties to alter system use or performance.

These provisions may become relevant if unauthenticated telemetry is actually used as training, validation, testing, monitoring, or operational input for a covered high-risk AI system. The existence of a telemetry collector alone does not prove that connection.

The AI Act’s implementation timeline has been phased and subject to continuing legislative developments, so current applicability dates should be verified before relying on it in a formal complaint.

### EU Cyber Resilience Act

The Cyber Resilience Act establishes cybersecurity requirements for covered products with digital elements and emphasizes secure design, vulnerability handling, and manufacturer responsibility.

It may be relevant where a telemetry collector is part of a covered connected product or remote data-processing solution. Its obligations are phased, so the applicable product category and effective date must be checked.

---

## United States federal considerations

### Federal Trade Commission Act — Section 5, 15 U.S.C. § 45

Section 5 prohibits unfair or deceptive acts or practices in or affecting commerce. The FTC has repeatedly used this authority in consumer privacy and data-security enforcement.

Potential relevance may arise where:

* A company makes representations about data accuracy, security, device authenticity, fraud protection, or privacy that are inconsistent with actual practices;
* Failure to control unauthenticated telemetry creates or is likely to create substantial consumer injury; or
* A company fails to address unreasonable data-security risks after receiving credible notice.

A vulnerability does not automatically establish an FTC Act violation. The actual processing, company representations, preventability of harm, and consumer impact matter.

### Gramm-Leach-Bliley Act Safeguards Rule

Covered financial institutions must maintain an information-security program designed to protect customer information. Risk assessments must consider threats to the security, confidentiality, and **integrity** of customer information, including how information could be misused, altered, or destroyed.

This may be relevant where unauthenticated telemetry enters systems operated by covered financial institutions or service providers and can affect customer information, fraud systems, financial decisions, or protected records.

### HIPAA Security Rule

For HIPAA-covered entities and business associates, the Security Rule requires protection of the confidentiality, integrity, and availability of electronic protected health information.

HIPAA defines integrity in terms of information not being altered or destroyed in an unauthorized manner. The rules include risk analysis, incident procedures, integrity controls, and mechanisms to authenticate electronic protected health information where reasonable and appropriate.

This may be directly relevant to telemetry involving patients, medical devices, health applications operating on behalf of covered entities, hospitals, insurers, or other regulated health systems.

### Children’s Online Privacy Protection Act and COPPA Rule

Operators subject to COPPA must establish and maintain reasonable procedures to protect the confidentiality, security, and integrity of personal information collected from children under 13.

This may be relevant when unauthenticated telemetry affects children’s accounts, devices, applications, precise locations, identifiers, or behavioral information.

### Fair Credit Reporting Act and Regulation V

The FCRA and Regulation V impose accuracy and integrity requirements on consumer-reporting agencies and entities that furnish consumer information.

This may be relevant if telemetry-derived information affects credit, employment screening, insurance eligibility, tenant screening, or another consumer-reporting function. It is not generally applicable to ordinary product analytics.

---

## California considerations

### California Civil Code § 1798.100(e)

Covered businesses must implement reasonable security procedures and practices appropriate to the nature of personal information and designed to protect it from unauthorized or illegal access, destruction, use, modification, or disclosure.

Unauthorized telemetry modification may be relevant if the event becomes personal information or alters information reasonably linkable to a California consumer or household.

### California Civil Code § 1798.106

California consumers have the right to request correction of inaccurate personal information maintained about them. Covered businesses receiving a qualifying request must use commercially reasonable efforts to correct the information.

A telemetry system may create a practical compliance problem if fabricated information is associated with a person but the company cannot locate, explain, distinguish, or correct the record.

### California Civil Code § 1798.81.5

Businesses that own, license, or maintain covered personal information about California residents must use reasonable security procedures and practices appropriate to the nature of that information and designed to protect against unauthorized access, destruction, use, modification, or disclosure.

### California Civil Code § 1798.91.04 — Connected devices

Manufacturers of covered connected devices must equip them with reasonable security features appropriate to the nature and function of the device and the information it collects, contains, or transmits.

This may be relevant where unauthenticated telemetry is part of the security architecture of a covered connected device. It does not necessarily govern every cloud collector or server-side endpoint.

### CCPA private-right-of-action limitation

The CCPA’s private right of action is substantially narrower than its general security and privacy obligations. Do not claim that telemetry injection automatically gives consumers a private lawsuit.

Private-action eligibility generally depends on a qualifying compromise involving specified personal information and the statutory requirements. Regulatory enforcement and consumer correction rights are separate questions.

---

## Other useful U.S. state authorities

### New York SHIELD Act

The SHIELD Act requires covered organizations possessing New York residents’ private information to develop, implement, and maintain reasonable safeguards.

It may be relevant where telemetry injection affects covered private information or demonstrates a weakness in administrative, technical, or physical security safeguards.

### Colorado Privacy Act

Covered controllers must take reasonable measures to secure personal data during storage and use from unauthorized acquisition. Colorado consumers also have rights to access, delete, and correct personal data.

This may be relevant where fabricated telemetry becomes associated with a Colorado consumer or is used for profiling or consequential decisions.

### Massachusetts 201 CMR 17.00

Massachusetts requires covered persons that own or license personal information about Massachusetts residents to maintain safeguards meeting minimum standards for paper and electronic records.

This may be relevant if unauthenticated telemetry affects the covered categories of Massachusetts personal information.

---

## Non-law standards that support the technical argument

### NIST SP 800-53 — System and Information Integrity

NIST SP 800-53 includes the System and Information Integrity control family and SI-7 controls concerning software, firmware, and information integrity.

These are not generally binding laws for private companies, but they provide recognized language for integrity checks, detection, notification, and response to integrity violations.

### NIST AI Risk Management Framework

The NIST AI RMF emphasizes trustworthy AI risk management. NIST specifically recognizes the importance of training-data provenance, data quality, integrity, and attribution.

This is useful when asking whether telemetry is used in an AI pipeline, but it does not prove that a particular telemetry source trains a model.

### NIST adversarial machine-learning terminology

NIST defines data poisoning as a poisoning attack in which an adversary controls part of the training data.

Use the phrase “potential data-poisoning pathway” until there is evidence that the accepted telemetry actually becomes part of training, validation, fine-tuning, reinforcement, or model-monitoring data.

---

## Claims to avoid without vendor confirmation

Do not state the following as confirmed merely because an endpoint returned HTTP 200 or an acceptance flag:

* The event was permanently stored;
* The event entered BigQuery, Pub/Sub, Scribe, Scuba, a data lake, or another specific internal platform;
* A fabricated device became associated with a real device or fleet;
* A payload containing XSS, SQL, or shell syntax was executed;
* A machine-learning model was trained on the event;
* A personal-data breach occurred;
* A breach-notification deadline was triggered;
* A particular privacy statute was violated;
* The company is always a controller or always a processor;
* The issue has a specific legal or CVSS severity without evidence of downstream effects.

Preferred language:

> The production collector accepted an unauthenticated, attacker-controlled, protocol-valid event. The vendor must determine whether the event was discarded, permanently classified as untrusted, associated with a legitimate resource, retained, aggregated, exported, or consumed by downstream systems.

And:

> If the event becomes associated with personal data, regulated devices, safety systems, financial decisions, health information, children’s data, or high-risk AI workflows, additional legal and regulatory obligations may be implicated.
