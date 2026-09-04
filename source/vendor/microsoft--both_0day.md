This is what me and Ken are working with:
the short story : we found telemetry injection 0days in both endpoints that feed into their only telemetry pool

the long story of both 0days:

Unauthenticated Telemetry Injection in Microsoft Power BI / Fabric Gateway Infrastructure
VULN-193698 6/7/26 still triaging 

SECTION 2: TELEMETRY INJECTION – APPLICATION INSIGHTS KEYS (CRITICAL)

Four Application Insights instrumentation keys accept unauthenticated POST requests to the public ingestion endpoint. No authentication or API key is required.

Injection Endpoint: https://eastus-8.in.applicationinsights.azure.com/v2.1/track

Confirmed Keys:
Key 	Source Application 	Status
6a66a822-429e-49e0-951f-dbba255ac842 	Power BI WFE 	CONFIRMED ACCEPTING
e3524ec5-ee88-4933-a91e-4d16e385ef93 	TriShell 	CONFIRMED ACCEPTING
e43fee4d-90d5-4c2a-a681-cffdd604ad5c 	Fabric Main App 	CONFIRMED ACCEPTING
433d8c1b-e63d-4935-8917-fbb39ecb7b51 	Fabric TriShell 	CONFIRMED ACCEPTING

The endpoint accepts telemetry in different formats
Bulk sends (10/10 events accepted)
Large payload injection (50KB+ accepted)
Persistent/heartbeat-style sends are possible

Second one :

Unauthenticated Telemetry Injection in Microsoft OneCollector Pipeline (browser.events.data.microsoft.com, vortex.data.microsoft.com)
Unauthenticated Telemetry Injection in Microsoft OneCollector Pipeline (browser.events.data.microsoft.com, vortex.data.microsoft.com)

VULN-200045 7/6/2026 active triage

The OneCollector telemetry pipeline accepts unauthenticated POST requests with the client-id=NO_AUTH parameter. Two endpoints (browser.events.data.microsoft.com and vortex.data.microsoft.com) return 204 No Content for arbitrary telemetry events with no authentication required.

A global API key (69adc3c768bd4dc08c19416121249fcc-66f1668a-797b-4249-95e3-6c6651768c28-7293) was discovered in the client-side source code of login.microsoftonline.com. This key can be used to inject arbitrary events into Microsoft's telemetry pipeline.

The injection supports:

    Basic event injection
    Bulk injection (10/10 events accepted)
    Large payload injection (50KB+)
    Steganographic C2 channels (commands hidden in ai.application.ver)
    Custom event properties

This is the same vulnerability pattern as VULN-193698 (App Insights injection), but affects a different telemetry pipeline.

9 OneCollector endpoints across global, regional, and mobile infrastructure accept unauthenticated telemetry injection using the same API key. All endpoints returned 204 for bulk injection tests (10/10 events accepted):
Endpoint 	Region/Purpose 	Test Result
browser.events.data.microsoft.com 	Browser telemetry 	10/10
vortex.events.data.microsoft.com 	General telemetry 	10/10
self.events.data.microsoft.com 	Global base endpoint 	10/10
v10.events.data.microsoft.com 	Global V10 endpoint 	10/10
us-mobile.events.data.microsoft.com 	US mobile 	10/10
eu-mobile.events.data.microsoft.com 	Europe mobile 	10/10
uk-mobile.events.data.microsoft.com 	UK mobile 	10/10
au-mobile.events.data.microsoft.com 	Australia mobile 	10/10
mobile.events.data.microsoft.com 	General mobile 	10/10

These endpoints represent Microsoft's entire OneCollector telemetry ingestion infrastructure, used by Windows, Office, Teams, Xbox, Azure Portal, Azure AD, and other Microsoft services.
Confirmed Attack Capabilities

All injection vectors have been validated on all 9 endpoints:
Attack Vector 	Result
Basic event injection 	204 on all endpoints
Bulk injection (10/10 events) 	204 on all endpoints
Large payload injection (50KB+) 	204 on all endpoints
Steganographic C2 channels 	Commands hidden in ai.application.ver
Multiple API keys 	2 keys confirmed working
New API Keys Found

We have discovered two working API keys from different Microsoft services:

    Azure AD Key: 69adc3c768bd4dc08c19416121249fcc-66f1668a-797b-4249-95e3-6c6651768c28-7293
    Origin: login.microsoftonline.com

    Azure Portal Key: d634483c08244c1ca09af2b2d952c92e-ab2bba03-2ba3-49d8-a82c-ef6da750d8ab-7725
    Origin: portal.azure.com

Both keys follow the same NO_AUTH pattern and work on all 9 endpoints.


DIAGRAM :

browser.events.data.microsoft.com
vortex.data.microsoft.com
          │
          ▼
     1DS Gateway (front-end, validates iKey/apiKey)
          │
          ▼
  ┌───────────────────┐
  │  OneCosmos / Kusto│ ← This is where it converges
  └───────────────────┘
          ▲
          │
dc.services.visualstudio.com (AppInsights)
