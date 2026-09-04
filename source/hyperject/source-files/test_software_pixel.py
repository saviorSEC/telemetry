#!/usr/bin/env python3


import requests
import json
import time
import random
from urllib.parse import urlencode

ENDPOINT = "https://www.facebook.com/tr"

def test_facebook_pixel():
    print("\n" + "="*70)
    print("="*70)
    
    # Generate fake pixel ID
    pixel_id = f"{random.randint(100000000000000, 999999999999999)}"
    
    test_cases = [
        {
            "name": "GET Request (Standard Pixel)",
            "method": "GET",
            "params": {
                "id": pixel_id,
                "ev": "PageView",
                "dl": "https://example.com",
                "rl": "",
                "if": "false",
                "ts": str(int(time.time() * 1000)),
                "cd": json.dumps({"test": "injection"}),
                "sw": "1920",
                "sh": "1080",
                "v": "2.9.123",
                "r": "stable",
                "ec": "0",
                "ex": "1",
                "fbp": f"fb.1.{int(time.time())}.{random.randint(1000000000, 9999999999)}",
                "it": str(int(time.time() * 1000)),
                "coo": "false",
                "eid": "noscript"
            }
        },
        {
            "name": "POST Request",
            "method": "POST",
            "params": {
                "id": pixel_id,
                "ev": "PageView",
                "dl": "https://example.com",
                "cd": json.dumps({"test": "post_injection"})
            }
        },
        {
            "name": "POST with JSON Body",
            "method": "POST",
            "body": {
                "data": [{
                    "event_name": "PageView",
                    "event_time": int(time.time()),
                    "user_data": {
                        "em": "test@example.com",
                        "ph": "1234567890"
                    }
                }]
            }
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n[+] Testing: {test['name']}")
        
        try:
            if test['method'] == "GET":
                url = f"{ENDPOINT}?{urlencode(test['params'])}"
                response = requests.get(url, timeout=10)
            else:
                if 'body' in test:
                    response = requests.post(
                        ENDPOINT,
                        json=test['body'],
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                else:
                    response = requests.post(
                        ENDPOINT,
                        data=test['params'],
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
        print("    Pixel accepts data")
        print("    Could inject fake conversion events")
    
    return results

if __name__ == "__main__":
    test_facebook_pixel()
