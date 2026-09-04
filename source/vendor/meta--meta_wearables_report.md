# Meta Bug Bounty - Updated Findings Report

**Report Number:** 122102502879389843  
**Researcher:** ek0ms  
**Date:** July 12, 2026  
**Contact:** ek0ms611@gmail.com

---

## Original Findings (Submitted)

The original report identified three unauthenticated telemetry injection endpoints in Meta's production infrastructure. All three endpoints accept arbitrary HTTP requests without authentication, authorization, or validation.

**Vulnerable Endpoints:**

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `https://www.facebook.com/tr` | Facebook Pixel event ingestion | 200 OK - UNAUTHENTICATED |
| `https://www.facebook.com/log` | Internal log ingestion | 200 OK - UNAUTHENTICATED |
| `https://www.facebook.com/metrics` | Internal metrics ingestion | 200 OK - UNAUTHENTICATED |

**Key Findings:**
- No authentication or authorization required on any endpoint
- The Pixel endpoint accepts ANY random 15-digit ID without validation
- No rate limiting detected (10 consecutive requests per endpoint, 30 total, accepted with 100% success)
- Various payload formats accepted (JSON, GET parameters, large payloads, nested JSON, unicode)
- Persistent injection capability demonstrated (heartbeat test with 5 rounds at 10-second intervals)

---

## New Findings

I have continued my research and identified additional Meta telemetry injection vectors affecting the **Smart Glasses / Wearables** ecosystem.

### Meta Wearables / Glasses Telemetry Attack Surface

Meta's Developer Analytics Tools (DAT) for Ray-Ban Meta Smart Glasses collects custom events, session metrics, and device telemetry. I have identified unauthenticated telemetry injection vectors in this pipeline.

### Confirmed Vulnerable App IDs

The following App IDs are confirmed to accept unauthenticated telemetry injection via the Pixel endpoint:

| App ID | Application | Category |
|--------|-------------|----------|
| 464891386855067 | Tinder | Lifestyle |
| 936619743392459 | Instagram Web | Social |
| 174829003346 | Spotify | Entertainment |
| 1405987639482438 | Plex | Entertainment |
| 9869919170 | The New York Times | Utilities |

### New Injection Vectors

**1. Pixel Injection Using App IDs**

Using App IDs as Pixel IDs, all tested endpoints accepted arbitrary telemetry:

```http
GET https://www.facebook.com/tr?id=464891386855067&ev=CustomEvent&cd[url]=XSS_PAYLOAD
```

| App ID | Application | Result |
|--------|-------------|--------|
| 464891386855067 | Tinder | 200 OK |
| 936619743392459 | Instagram Web | 200 OK |
| 174829003346 | Spotify | 200 OK |
| 1405987639482438 | Plex | 200 OK |
| 9869919170 | The New York Times | 200 OK |

**2. Glasses-Specific Telemetry Injection**

The following glasses-specific event types were tested and accepted:

| Event Type | Description | Result |
|------------|-------------|--------|
| VOICE_COMMAND | Voice command telemetry | 200 OK |
| AI_QUERY | AI query telemetry | 200 OK |
| MEDIA_CAPTURE | Media capture events | 200 OK |
| BUTTON_PRESS | Button press telemetry | 200 OK |
| DEVICE_STATUS | Device status updates | 200 OK |
| GLASSES_BATTERY | Battery telemetry | 200 OK |
| GLASSES_CONNECTIVITY | Connectivity telemetry | 200 OK |
| GLASSES_SENSOR | Sensor telemetry | 200 OK |

**3. XSS Payload Injection**

XSS canary payloads were accepted across all tested endpoints:

| Payload Type | Example | Status |
|--------------|---------|--------|
| Script fetch | `<script>fetch('https://CALLBACK')</script>` | ACCEPTED |
| Image onerror | `<img src=x onerror=fetch('https://CALLBACK')>` | ACCEPTED |
| SVG onload | `<svg onload=fetch('https://CALLBACK')>` | ACCEPTED |
| Body onload | `<body onload=fetch('https://CALLBACK')>` | ACCEPTED |
| Voice command | Voice command with XSS payload | ACCEPTED |
| AI query | AI query with XSS payload | ACCEPTED |

**4. Bulk Injection Results**

| Test | Result |
|------|--------|
| 10 requests per endpoint | 10/10 accepted (100%) |
| Heartbeat (5 rounds) | 5/5 accepted (100%) |

---

## Updated Global Context

This vulnerability class - unauthenticated telemetry injection has been confirmed across multiple major technology companies:

| Company | Case ID | Status |
|---------|---------|--------|
| Google | OE110716814418 | S2/P2 Active Investigation |
| Microsoft | VULN-193698, VULN-200045 | Active Triage |
| Apple | Pending | Under Review |
| Baidu | Pending | Reporting Soon |
| CNZZ/Umeng | Pending | Reporting Soon |
| Tencent | Pending | Reporting Soon |
| Matomo | Pending | confirmed and still testing |
| Tencent | Pending | confirmed and still testing|

---

## Summary of New Vulnerabilities

| Test | Endpoint | Result |
|------|----------|--------|
| Basic Event Injection | `/tr` with App IDs | PASS (200 OK) |
| XSS Payloads (6 variants) | `/tr` with App IDs | PASS (200 OK) |
| Glasses-Specific Events (8 types) | `/tr` with App IDs | PASS (200 OK) |
| Bulk Injection (10/10) | `/tr` with App IDs | PASS (100%) |
| Heartbeat Injection (5/5) | `/tr` with App IDs | PASS (100%) |

**All tested App IDs confirmed vulnerable to unauthenticated telemetry injection.**

---

## Continued Research

I intend to continue investigating related attack vectors, particularly:
- Graph API endpoints (`/activities`, `/events`) with App IDs
- The Smart Glasses telemetry dashboard (developers.meta.com/dat) for data reflection
- Conversions API endpoints and event_source_url injection

I will provide updates as my research progresses.

# NEW Attached POCs and Screenshots

payloads.png
injection_test.png
wearables_recon.py
recon.png
test_xss.py
batch_injection.py


---

**Researcher:** ek0ms  
**Contact:** ekoms611@gmail.com
**Report Number:** 122102502879389843  
**Date:** July 12, 2026
