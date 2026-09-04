#!/usr/bin/env python3


import requests
import json
import time
import random

ENDPOINT = "https://h.trace.qq.com/kv"

def test_tencent_trace():
    print("\n" + "="*70)
    print("="*70)
    
    # Tencent trace format examples
    test_cases = [
        {
            "name": "Key-Value Format",
            "data": f"test_key=test_value&timestamp={int(time.time())}&device_id={random.randint(100000, 999999)}",
            "content_type": "application/x-www-form-urlencoded"
        },
        {
            "name": "JSON Format",
            "payload": {
                "key": "test_event",
                "value": "test_data",
                "timestamp": int(time.time()),
                "device_id": f"DEVICE_{random.randint(100000, 999999)}"
            },
            "content_type": "application/json"
        },
        {
            "name": "Tracking Pixel",
            "data": f"act=test&aid={random.randint(100000, 999999)}&t={int(time.time())}",
            "content_type": "application/x-www-form-urlencoded"
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n[+] Testing: {test['name']}")
        print(f"    Content-Type: {test['content_type']}")
        
        try:
            if test['content_type'] == 'application/json':
                response = requests.post(
                    ENDPOINT,
                    json=test['payload'],
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            else:
                response = requests.post(
                    ENDPOINT,
                    data=test['data'],
                    headers={"Content-Type": test['content_type']},
                    timeout=10
                )
            
            print(f"    Status: {response.status_code}")
            
            if response.status_code in [401, 403]:
                print("    🔒 Authentication Required")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": True
                })
            elif response.status_code in [200, 204]:
                print("    ✅ ACCEPTED!")
                if response.text:
                    print(f"    Response: {response.text[:200]}")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": False,
                    "accepted": True
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
    accepted = any(r.get('accepted', False) for r in results)
    
    print(f"\n[+] Authentication Required: {'✅ Yes' if auth_required else '❌ No'}")
    print(f"[+] Requests Accepted: {'✅ Yes' if accepted else '❌ No'}")
    
    if not auth_required and accepted:
        print("\n[!] VULNERABILITY INDICATED:")
        print("    No authentication required")
        print("    Endpoint accepts data")
    
    return results

if __name__ == "__main__":
    test_tencent_trace()
