# Unauthenticated Telemetry Injection and the Collapse of Data Provenance

## Security Implications When Untrusted Telemetry Is Stored Alongside Trusted Production Data

**Author:** ek0ms savi0r, based on technical reports, vendor correspondence, proof-of-concept results, and research conducted by ek0ms savi0r, k3nundrum & TJnull / Church of Malware
**Date:** June-September 2026

---

## Executive Summary

Modern software systems produce enormous quantities of telemetry. Applications, browsers, operating systems, mobile devices, cloud services, vehicles, security platforms, and web applications continuously submit events describing what users and systems appear to be doing.

That data is frequently treated as operational truth.

Telemetry feeds dashboards, application-performance monitoring, usage analytics, alerting systems, fraud systems, business intelligence, incident investigations, attribution pipelines, and increasingly automated decision-making systems.

The research reviewed for this paper demonstrates a recurring architectural characteristic across several major telemetry ecosystems: externally controlled clients can submit synthetic telemetry to production ingestion endpoints without authenticating the producer as an authoritative source.

The most important security question is not simply whether an endpoint accepts unauthenticated data.

The critical question is:

> **What happens to that data after acceptance?**

If externally supplied telemetry is discarded, quarantined, or permanently marked by the server as untrusted and that provenance survives every downstream transformation, the security implications may be limited.

If, however, attacker-supplied telemetry is stored, aggregated, queried, exported, or otherwise processed alongside genuine production telemetry without durable and authoritative provenance, the result is a fundamental data-integrity problem.

The system can no longer reliably answer a deceptively simple question:

**Which records actually came from the systems they claim to represent?**

That distinction matters enormously in an era where telemetry is no longer merely diagnostic information. Telemetry increasingly serves as evidence.

My conclusion from the research reviewed here is that unauthenticated telemetry ingestion should be analyzed as a **data-provenance and trust-boundary problem**, rather than dismissed merely because an ingestion endpoint was intentionally designed to receive data from untrusted client environments.

The mere existence of unauthenticated ingestion does not establish a vulnerability.

But storing indistinguishable attacker-generated and authentic production records in the same trust domain can.

---

# 1. Introduction

Telemetry systems historically occupied a relatively simple role.

Applications emitted logs.

Developers looked at them.

If someone inserted junk into a diagnostic dataset, the consequences might have been little more than confusing charts.

That model no longer reflects modern infrastructure.

Telemetry now drives:

* observability;
* security monitoring;
* application performance analytics;
* incident response;
* attribution;
* user and session reconstruction;
* fraud detection;
* product analytics;
* alerting;
* capacity planning;
* automated remediation;
* operational decision making;
* data warehouses;
* artificial-intelligence and machine-learning pipelines.

The value of telemetry has therefore changed.

So has the importance of knowing where it came from.

During research into multiple telemetry platforms, Church of Malware identified several production ingestion interfaces that accepted synthetic externally generated events.

Examples investigated included Microsoft Application Insights, Microsoft's OneCollector/1DS ecosystem, Google's Android Check-In infrastructure, TikTok analytics ingestion, and Flock Safety's use of third-party analytics infrastructure.

The implementations differed.

The unanswered architectural question repeatedly remained the same:

**Does the backend maintain an immutable distinction between externally unverified telemetry and telemetry originating from an authoritative producer?**

This paper examines why that distinction matters.

---

# 2. The Fundamental Security Property: Provenance

Data provenance describes the origin and history of information.

For telemetry, meaningful provenance should answer questions such as:

* Which producer generated this record?
* Was that producer authenticated?
* Was the record submitted by a first-party application, browser client, external script, or another source?
* Has the record been modified?
* Which transformations have been applied?
* Has its trust classification changed?
* Can the originating client alter that classification?
* Does the classification survive aggregation, export, indexing, and downstream processing?

A telemetry system does not necessarily need to reject untrusted data.

But it must understand that it is untrusted.

That distinction is fundamental.

Consider two records:

```text
Event A:
user_id = 483920
operation = checkout
status = failed
source = authenticated-production-client
```

and

```text
Event B:
user_id = 483920
operation = checkout
status = failed
source = unknown-external-producer
```

These records may contain identical application data.

They are not equivalent evidence.

If the provenance field disappears during processing, the system has transformed two fundamentally different observations into apparently equivalent facts.

That is where telemetry injection becomes significantly more interesting from a security perspective.

---

# 3. Ingestion Is Not the Same as Impact

A major lesson from this research is the necessity of separating what external testing can prove from what only the telemetry operator can determine.

For example, several tested services returned responses demonstrating that submitted telemetry was accepted by the ingestion boundary.

Microsoft Application Insights returned responses of the form:

```json
{
  "itemsReceived": 1,
  "itemsAccepted": 1,
  "appId": "b784cd90-1562-4630-bb8f-af8af0d05305",
  "errors": []
}
```

Google's Android Check-In service returned:

```json
{
  "stats_ok": true,
  "time_msec": 1784330187681
}
```

Those responses are meaningful.

They demonstrate that the remote service received and parsed externally supplied telemetry.

They do **not**, by themselves, prove:

* permanent storage;
* dashboard visibility;
* trusted attribution;
* alert generation;
* business-metric manipulation;
* query visibility;
* machine-learning poisoning;
* SOC impact;
* billing impact;
* execution of submitted content;
* cross-tenant effects.

This distinction is essential.

A responsible technical analysis should therefore divide the problem into two layers.

### Layer One: Externally Verifiable

The researcher can determine whether:

* authentication is required;
* arbitrary clients can reach the collector;
* synthetic events are accepted;
* selected fields are caller controlled;
* valid production destination identifiers are recognized;
* basic volume is tolerated;
* the server acknowledges successful ingestion.

### Layer Two: Operator-Verifiable

Only the telemetry provider or customer can normally determine:

* final storage disposition;
* trust classification;
* retention;
* filtering;
* aggregation;
* dashboard appearance;
* alert participation;
* export behavior;
* downstream analytics use;
* server-side provenance;
* whether untrusted records remain distinguishable from authentic ones.

This difference created a recurring difficulty during coordinated disclosure.

Researchers can prove entry into the front door.

Vendors control the rooms behind it.

---

# 4. The Threat Model

The relevant attacker does not necessarily need privileged access.

The attacker may simply possess information already delivered to legitimate client software.

Many telemetry platforms intentionally expose destination identifiers in browser applications or client software.

For example, an Application Insights instrumentation key should not automatically be described as a secret credential.

It identifies a telemetry destination.

That design decision is not itself a security flaw.

The problem arises if possession of that public identifier allows an arbitrary external producer to generate telemetry that later becomes operationally indistinguishable from authentic application telemetry.

The attacker therefore does not need to steal the identity of an authorized administrator.

The attacker attempts to impersonate **the data-producing environment**.

This distinction matters.

Traditional authentication asks:

> Who is allowed to access the application?

Telemetry provenance asks:

> Who is allowed to create evidence describing what happened inside the application?

Those are different trust boundaries.

---

# 5. Evidence Observed Across Multiple Ecosystems

## Microsoft Application Insights

Testing demonstrated externally submitted synthetic envelopes being accepted by Application Insights ingestion endpoints.

In one third-party deployment associated with CarMax, synthetic records containing caller-controlled values were accepted for fields representing:

* event names;
* user identifiers;
* session identifiers;
* operation names;
* operation IDs;
* arbitrary custom properties;
* dependency record names;
* dependency targets;
* result codes;
* success states.

A synthetic dependency record was accepted as telemetry.

That does not mean the dependency was actually executed.

It means a caller was able to create a record claiming that such a dependency existed.

That distinction demonstrates precisely why provenance matters.

A monitoring system must distinguish between:

```text
"The application observed dependency X failing."
```

and:

```text
"An unknown external party submitted a record claiming dependency X failed."
```

If those become equivalent downstream, monitoring integrity is weakened.

---

## Microsoft OneCollector / 1DS

Research into Microsoft's OneCollector infrastructure identified multiple collection endpoints accepting externally supplied events.

The broader significance was not merely the number of endpoints.

OneCollector is infrastructure used across a large ecosystem of Microsoft products.

Microsoft's position was that backend validation, filtering, and trust-handling mechanisms protect downstream use.

That response highlights the central issue of this paper.

Those controls are exactly what matter.

But architectural assertions are weaker evidence than an end-to-end trace demonstrating how a specific synthetic canary was treated.

The unresolved question becomes:

> Was the submitted record actually traced through the production pipeline and shown to retain an immutable untrusted classification?

Without that information, external research can confirm ingestion but cannot independently verify downstream provenance.

---

## Google Android Check-In

Google's Android Check-In infrastructure accepted synthetic check-in data without requiring an already established device identity.

Google explained that unauthenticated bootstrap check-ins are expected because newly initialized devices must communicate before every identity relationship exists.

Architecturally, that explanation is reasonable.

It also reinforces why authentication alone is not the complete question.

A telemetry system may legitimately need to accept an unauthenticated record.

The security property therefore shifts from:

```text
Reject unauthenticated data.
```

to:

```text
Never allow unauthenticated data to silently acquire the trust characteristics of authenticated data.
```

Google later stated that server-controlled mechanisms classify and segregate unauthenticated inputs.

If those controls operate as described and persist through downstream processing, they represent the kind of provenance architecture necessary for safely handling untrusted telemetry.

The difficulty for an external researcher is independently verifying that claim.

---

## TikTok Analytics

TikTok's analytics infrastructure similarly demonstrated the distinction between ingestion design and downstream trust.

A duplicate HackerOne report confirmed that the endpoint behavior had previously been reported.

The prior issue had been classified as non-security-sensitive because analytics and lead information were considered unreliable or non-mission-critical within that threat model.

That position may be defensible for certain analytics environments.

But it raises a larger architectural question:

If a company explicitly assumes analytics records may be unreliable, where is that assumption enforced?

Is unreliability:

* merely documented;
* understood by engineers;
* encoded as metadata;
* or cryptographically/server-authoritatively preserved with each record?

The difference matters.

A human understanding that "analytics can be noisy" is not equivalent to machine-readable provenance.

---

## Flock Safety and Segment

Research involving a Flock Safety deployment demonstrated another common architecture: a first-party organization forwarding telemetry through a third-party analytics platform.

That architecture expands the provenance problem.

The lifecycle may become:

```text
Client
  ↓
Third-party collector
  ↓
Transformation
  ↓
First-party analytics
  ↓
Warehouse
  ↓
Dashboard / alert / model
```

Trust metadata must survive every boundary.

If an ingestion provider knows that an event came from an unauthenticated producer but that classification disappears when the event is exported downstream, the security control has effectively failed.

Provenance must therefore be durable, not temporary.

---

# 6. What Happens If Fake and Real Telemetry Are Stored Together?

This is the most important question.

Suppose a production telemetry system stores both authentic records and externally generated synthetic records.

There are two fundamentally different architectures.

### Architecture A: Provenance Preserved

```text
REAL EVENT
producer_trust = verified

FAKE EVENT
producer_trust = external_unverified
```

Both records may exist in the same physical datastore.

That may be acceptable.

Systems can query, filter, quarantine, or weight the records differently.

### Architecture B: Provenance Lost

```text
REAL EVENT
user_id = 123
operation = login

FAKE EVENT
user_id = 123
operation = login
```

There is no authoritative property distinguishing the two.

This is significantly more dangerous.

The following consequences become possible.

---

## 6.1 Loss of Evidentiary Integrity

Telemetry frequently becomes forensic evidence.

Incident responders may ask:

* When did the user log in?
* What operation failed?
* Which dependency was contacted?
* Which session generated the request?
* Which software version produced the event?
* What occurred immediately before the outage?

If arbitrary external actors can manufacture records indistinguishable from genuine records, telemetry becomes unreliable evidence.

This does not necessarily make the entire datastore useless.

But every affected record becomes epistemically weaker.

The organization no longer merely has a logging problem.

It has an evidence-authenticity problem.

---

# 7. False Operational Narratives

Modern telemetry systems reconstruct narratives.

A dashboard might appear to show:

```text
User 432 logged in
↓
Started checkout
↓
Called payment dependency
↓
Dependency failed
↓
Session abandoned
```

An injected record can fabricate pieces of that narrative.

With enough control over event fields, synthetic telemetry could theoretically create observations claiming:

* users performed actions they did not perform;
* operations failed when they did not;
* dependencies existed when they did not;
* sessions behaved differently from reality;
* application versions generated events they never generated.

Again, whether a specific system consumes such injected data is an empirical downstream question.

But if fake records and authentic records lose provenance, the dataset supports narratives that are not necessarily grounded in observed reality.

---

# 8. Detection and Monitoring Consequences

Security monitoring depends heavily on assumptions about data trust.

A detection might effectively mean:

```text
IF event.type = authentication_failure
AND count > threshold
THEN alert
```

If an external producer can manufacture events contributing to that query, false positives become possible.

The opposite risk also exists.

Attackers do not always need to fabricate obvious malicious telemetry.

They can manufacture noise.

Consider a real malicious event surrounded by thousands of misleading records.

The objective may not be to erase the authentic signal.

It may simply be to reduce analyst confidence.

The attacker attacks the **signal-to-noise ratio**.

This is particularly relevant to security operations because analyst trust is itself a limited resource.

If a telemetry source repeatedly produces unexplainable false events, defenders eventually downgrade its reliability.

That creates an indirect attack against detection capability.

---

# 9. Attribution Failure

Telemetry frequently contains apparent identities:

```text
user_id
session_id
device_id
operation_id
account_id
tenant_id
application_version
hostname
```

But the existence of an identity field does not mean the producer was authorized to assert that identity.

This is one of the most important distinctions in telemetry security.

A field saying:

```text
user_id = Alice
```

does not mean Alice generated the event.

It means the event **claims** Alice generated it.

Without authenticated provenance, attribution fields should be treated as assertions made by the producer rather than authoritative facts.

Systems that fail to preserve that distinction risk confusing:

```text
claimed identity
```

with:

```text
verified identity
```

That is a classic trust-boundary mistake.

---

# 10. Business Analytics Integrity

Telemetry often feeds more than security systems.

Organizations use it to answer questions such as:

* Which features are most popular?
* Which pages fail?
* Which regions experience errors?
* Which application version performs poorly?
* Which campaign generated conversions?
* Which customer journey failed?
* Which product requires engineering attention?

If unauthenticated records participate in these calculations without provenance controls, metrics can become polluted.

An attacker may not need to compromise a server.

They may instead compromise what the organization believes about the server.

That can produce incorrect operational decisions.

Examples could include:

* engineering teams investigating nonexistent failures;
* product teams prioritizing fabricated usage patterns;
* analysts calculating incorrect conversion rates;
* reliability teams responding to synthetic error spikes.

The exact feasibility depends on the downstream pipeline.

But the architectural risk is real whenever untrusted inputs become indistinguishable from trusted observations.

---

# 11. Artificial Intelligence Raises the Stakes

The growing use of telemetry in machine-learning and AI systems makes provenance significantly more important.

Not every telemetry dataset becomes training data.

Therefore unauthenticated ingestion alone does **not** prove machine-learning poisoning.

That claim requires evidence.

However, the general risk is straightforward.

Machine learning assumes that training and evaluation datasets provide meaningful observations of the environment being modeled.

If a dataset contains adversarially generated observations that cannot be distinguished from genuine observations, several problems emerge:

* corrupted training distributions;
* distorted anomaly baselines;
* incorrect labels;
* fabricated behavioral patterns;
* model drift;
* reduced confidence in training data;
* difficulty reconstructing dataset lineage.

This becomes especially dangerous when telemetry is repeatedly transformed.

A raw event may become:

```text
Raw telemetry
→ normalized event
→ daily aggregate
→ warehouse table
→ feature vector
→ model-training dataset
```

At the final stage, the original producer may no longer even be represented.

This is why provenance must survive transformation.

It is not enough to know that the original collector once knew an event was untrusted.

That fact must remain attached to the information derived from it.

---

# 12. The Aggregation Problem

Aggregation is one of the easiest ways to accidentally destroy provenance.

Imagine:

```text
99 genuine failures
1 attacker-generated failure
```

The system produces:

```text
failure_count = 100
```

Where is the provenance now?

Even if the attacker-generated record originally carried an untrusted designation, the aggregate may not.

A secure aggregation system may need to calculate something closer to:

```text
verified_failure_count = 99
unverified_failure_count = 1
```

or ensure that unverified records never contribute to security-sensitive aggregates.

This demonstrates an important point:

**Provenance is not merely a property of raw records.**

It must become a property of derived information.

---

# 13. Trust Must Be Server Controlled

A client cannot authoritatively declare itself trusted.

During research, synthetic records sometimes included explicit properties indicating that they were externally generated research data.

Those labels were useful for canary tracing.

They were not security controls.

An attacker controls client-submitted fields.

Therefore something like:

```json
{
  "producer_claim": "UNAUTHENTICATED_EXTERNAL_RESEARCHER"
}
```

does not prove that the server safely classified the record.

The security-relevant property must originate from the receiving infrastructure itself.

For example:

```text
producer_verification = unauthenticated
```

must be generated or cryptographically validated by the service.

The external sender must not be able to:

* remove it;
* change it;
* imitate a trusted value;
* suppress it;
* cause downstream systems to ignore it.

This principle is critical.

**Trust labels controlled by the untrusted party are not trust labels.**

---

# 14. Durable Provenance

A strong telemetry security architecture should maintain provenance through the entire lifecycle:

```text
Producer
↓
Ingress
↓
Queue
↓
Normalization
↓
Storage
↓
Transformation
↓
Aggregation
↓
Query
↓
Export
↓
Security analytics
↓
Business analytics
↓
Machine-learning pipelines
```

At every stage, systems should know whether the underlying information originated from:

```text
verified producer
unverified producer
mixed provenance
unknown provenance
```

If provenance disappears at any stage, downstream systems may unknowingly increase the trust assigned to the data.

That is effectively a form of privilege escalation for information.

The data enters as untrusted.

It emerges as trusted.

---

# 15. Telemetry Has a Trust Boundary

Security engineering traditionally treats request inputs as untrusted.

Telemetry deserves the same treatment.

Consider this common mental model:

```text
Internet
   ↓
Application API
   ↓
Authentication
   ↓
Authorization
```

Organizations carefully defend that boundary.

But another boundary often exists:

```text
Internet
   ↓
Telemetry collector
   ↓
Data warehouse
   ↓
Detection system
   ↓
Human / automated decisions
```

The telemetry collector may intentionally permit unauthenticated access.

That does not eliminate the trust boundary.

It merely moves the boundary deeper into the system.

The architecture must therefore enforce trust somewhere else.

If it does not, an externally writable telemetry collector becomes an externally writable source of organizational evidence.

---

# 16. Availability and Economic Effects

Unauthenticated ingestion can also create resource-consumption concerns.

Potential effects include:

* ingestion volume;
* retention volume;
* processing cost;
* indexing;
* export bandwidth;
* query complexity;
* dashboard noise;
* analyst time.

However, researchers should avoid automatically describing small-scale acceptance tests as proof of denial-of-service capability or absence of rate limiting.

For example:

```text
10/10 requests accepted
```

means only that throttling was not observed during that limited sample.

It does not prove:

```text
unlimited ingestion
```

or:

```text
no rate limiting exists.
```

This distinction illustrates a broader principle followed throughout this research:

**state what the evidence proves, then clearly identify what requires vendor-side validation.**

---

# 17. Why "The Telemetry Is Already Untrusted" Is Not a Complete Answer

A common response to this issue is:

> Browser telemetry is inherently untrusted.

That statement can be correct.

But it does not resolve the architectural problem.

If telemetry is inherently untrusted, downstream systems must know that.

The correct question is therefore not:

```text
Does engineering understand that browsers can lie?
```

It is:

```text
Can downstream systems technically distinguish unverified browser telemetry from telemetry carrying stronger producer guarantees?
```

Human awareness is not a security boundary.

Server-enforced metadata is.

---

# 18. Why "The Key Is Public" Is Also Not a Complete Answer

Another common response is:

> The instrumentation key is not a secret.

Correct.

For systems such as browser-based telemetry, destination identifiers often cannot realistically remain secret.

But secrecy of the destination identifier is not the central issue.

The real question is:

> Does knowing the public destination identifier grant the ability to create records that downstream systems treat as if they originated from the legitimate application?

The solution is therefore usually not:

```text
hide the key better
```

but:

```text
authenticate producers where appropriate
and/or
preserve authoritative untrusted provenance where authentication is impossible
```

---

# 19. Recommended Security Model

A resilient telemetry architecture should implement several complementary controls.

### Producer Authentication

Where feasible, authenticate high-trust telemetry producers.

Backend services, administrative systems, security sensors, and other authoritative systems should generally have stronger producer authentication than arbitrary browser clients.

### Server-Controlled Provenance

Every accepted event should receive an immutable provenance classification.

For example:

```text
producer_class = browser_unverified
producer_class = authenticated_backend
producer_class = first_party_device_attested
producer_class = third_party_integration
```

### Provenance-Aware Queries

Security-sensitive queries should explicitly define which producer classes are permitted to contribute.

### Provenance-Preserving Aggregation

Derived metrics must retain information about the trust level of their inputs.

### Separation of Trust Domains

Where practical, high-trust telemetry and inherently untrusted analytics data should use separate resources or pipelines.

### Canary Traceability

Operators should be capable of tracing a synthetic event from ingress through final disposition.

This is extremely useful for both security testing and incident investigation.

### Rate and Abuse Controls

Even intentionally public ingestion endpoints should monitor abnormal producer behavior and resource consumption.

### Documentation

Customers should understand whether client telemetry is authenticated, what guarantees exist, and which security-sensitive decisions should or should not rely on it.

---

# 20. A Better Vulnerability-Assessment Model

I believe telemetry-injection reports are often evaluated using an incomplete binary model:

```text
Is authentication required?
YES / NO
```

A better model asks four questions.

### 1. Can an external producer submit telemetry?

This establishes accessibility.

### 2. What fields can that producer control?

This establishes semantic influence.

### 3. Does the server authoritatively label the producer's trust level?

This establishes provenance.

### 4. Does that provenance survive every downstream use?

This establishes whether the architecture actually preserves the trust boundary.

This four-stage model produces much more meaningful security analysis than simply categorizing every unauthenticated telemetry endpoint as either "critical" or "working as designed."

The truth usually lies in the downstream architecture.

---

# 21. Vendor Validation Should Be Trace Based

When a researcher provides a unique synthetic canary, the strongest vendor response is not:

> We have protections.

It is:

> We located canary X. It entered system A, was assigned server-controlled classification B, was rejected from pipeline C, retained in store D for N hours, never contributed to aggregate E, and was not exported to system F.

That is evidence.

It enables both the researcher and vendor to reach a technically defensible conclusion.

Canary tracing should become a standard part of telemetry security triage.

It answers the question external researchers frequently cannot answer themselves:

**Where did the data actually go?**

---

# 22. Severity Should Follow Downstream Trust

Not every instance of unauthenticated telemetry ingestion should receive the same severity.

Severity should depend heavily on downstream behavior.

A conceptual model could look like this:

| Architecture                                              | Likely Security Concern       |
| --------------------------------------------------------- | ----------------------------- |
| Unauthenticated ingestion, immediately discarded          | Minimal                       |
| Unauthenticated ingestion, quarantined and clearly marked | Low                           |
| Stored but permanently marked untrusted                   | Context dependent             |
| Aggregated with trusted data but provenance preserved     | Moderate/context dependent    |
| Indistinguishable from trusted telemetry                  | Significant integrity concern |
| Drives security automation or authoritative decisions     | Potentially high              |
| Influences safety-critical or security-critical systems   | Potentially severe            |

The critical variable is not simply whether fake telemetry can enter.

It is whether fake telemetry can acquire the authority of real telemetry.

---

# 23. Broader Implications for Cybersecurity

Cybersecurity traditionally focuses heavily on confidentiality and system compromise.

Telemetry injection emphasizes another security property:

**epistemic integrity.**

Can the organization trust what its systems tell it happened?

That question becomes increasingly important as infrastructure becomes more autonomous.

If machines make decisions based on telemetry, then controlling the telemetry can become a way of indirectly influencing the machine.

An attacker may not need to compromise the decision engine.

They may only need to contaminate the evidence presented to it.

This concept extends well beyond the platforms examined during this research.

It applies to:

* cloud observability;
* endpoint telemetry;
* IoT systems;
* industrial monitoring;
* autonomous systems;
* mobile ecosystems;
* advertising analytics;
* fraud systems;
* security telemetry;
* artificial-intelligence pipelines.

The security industry has spent decades learning to distrust user input.

It must now learn to distrust **user-generated evidence**.

---

# 24. Researcher Responsibility

Telemetry research also requires restraint.

A successful HTTP response can be exciting evidence.

It is easy to overinterpret.

Responsible reporting should clearly distinguish between:

```text
confirmed ingestion
```

and:

```text
confirmed downstream impact.
```

Researchers should prefer unique harmless canaries over destructive payloads.

Once ingestion is demonstrated, additional production testing frequently provides diminishing value.

The vendor is better positioned to trace the submitted canary internally.

This reduces operational risk while producing better technical evidence.

The strongest report is not the one containing the most dramatic claims.

It is the one in which every claim can survive adversarial scrutiny.

---

# 25. Final Assessment

The research reviewed for this paper does not establish that every unauthenticated telemetry collector is insecure.

It establishes something more useful:

**Unauthenticated telemetry ingestion creates a trust problem that must be resolved somewhere in the architecture.**

There are only a few possible outcomes.

The data can be rejected.

It can be accepted but permanently identified as untrusted.

It can be segregated.

It can be prevented from influencing security-sensitive systems.

Or its origin can be forgotten.

That final possibility is the dangerous one.

If attacker-generated telemetry is stored alongside authentic production telemetry and no durable server-controlled provenance survives, then the organization loses the ability to reliably distinguish observation from assertion.

At that point, the issue is no longer merely that someone can "send fake analytics."

The attacker has acquired the ability to manufacture evidence.

And modern computing systems make enormous numbers of decisions from evidence.

That is why telemetry provenance deserves to become a first-class security property.

---

## Conclusion

The central lesson from this research can be summarized in one sentence:

> **A telemetry pipeline is only as trustworthy as its ability to preserve the difference between data it observed and data someone merely claimed was true.**

Unauthenticated ingestion may sometimes be necessary.

Untraceable provenance is not.

As telemetry increasingly feeds security operations, automated decision systems, artificial intelligence, business analytics, and critical infrastructure, the industry must stop treating telemetry as passive exhaust.

Telemetry is evidence.

Evidence requires provenance.

And when fake evidence becomes indistinguishable from real evidence, the problem is no longer simply telemetry injection.

It is a failure of trust.

