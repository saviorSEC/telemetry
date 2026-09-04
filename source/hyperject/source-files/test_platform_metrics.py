#!/usr/bin/env python3


import requests
import json
import time
import random

ENDPOINT = "https://metrics.icloud.com/metrics"

def test_apple_metrics():
    print("\n" + "="*70)
    print("="*70)
    
    # Test with various payloads
    test_cases = [
        {
            "name": "Basic JSON",
            "payload": {"test": "injection", "timestamp": int(time.time())},
            "content_type": "application/json"
        },
        {
            "name": "iCloud Metrics Format",
            "payload": {
                "metrics": [{
                    "name": "test_metric",
                    "value": random.randint(1, 100),
                    "timestamp": int(time.time() * 1000),
                    "device_id": f"TEST-{random.randint(100000, 999999)}"
                }]
            },
            "content_type": "application/json"
        },
        {
            "name": "Plain Text",
            "payload": "test_data",
            "content_type": "text/plain"
        },
        {
            "name": "Form Data",
            "payload": {"metric": "test", "value": "1"},
            "content_type": "application/x-www-form-urlencoded"
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n[+] Testing: {test['name']}")
        print(f"    Content-Type: {test['content_type']}")
        
        try:
            response = requests.post(
                ENDPOINT,
                json=test['payload'] if test['content_type'] == 'application/json' else test['payload'],
                headers={"Content-Type": test['content_type']},
                timeout=10,
                verify=True
            )
            
            print(f"    Status: {response.status_code}")
            
            # Check for authentication requirement
            if response.status_code in [401, 403]:
                print("    🔒 Authentication Required")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": True
                })
            elif response.status_code == 200:
                print(f"    ✅ ACCEPTED!")
                print(f"    Response: {response.text[:200]}")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": False,
                    "response": response.text[:200]
                })
            else:
                print(f"    ℹ️ Status: {response.status_code}")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": False
                })
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append({
                "test": test['name'],
                "status": "error",
                "error": str(e)
            })
        
        time.sleep(0.2)
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY")
    print("="*70)
    
    auth_required = any(r.get('auth_required', False) for r in results)
    accepted = any(r.get('status') == 200 for r in results)
    
    print(f"\n[+] Authentication Required: {'✅ Yes' if auth_required else '❌ No'}")
    print(f"[+] Requests Accepted: {'✅ Yes' if accepted else '❌ No'}")
    
    if not auth_required and accepted:
        print("\n[!] VULNERABILITY INDICATED:")
        print("    No authentication required")
        print("    Endpoint accepts data")
        print("    Potential for telemetry injection")
    
    return results

if __name__ == "__main__":
    test_apple_metrics()
