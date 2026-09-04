#!/usr/bin/env python3

import requests
import time
import random
from urllib.parse import urlencode

ENDPOINT = "https://hm.baidu.com/hm.gif"

def test_baidu_analytics():
    print("\n" + "="*70)
    print("="*70)
    
    # Generate fake tracking ID
    site_id = f"{random.randint(10000000, 99999999)}"
    
    test_cases = [
        {
            "name": "Standard Tracking Pixel",
            "params": {
                "si": site_id,
                "et": "0",
                "ep": "test_event",
                "el": "test_label",
                "ev": str(random.randint(1, 100)),
                "st": str(int(time.time())),
                "su": "https://example.com",
                "sr": "1920x1080",
                "sd": "24-bit",
                "en": "zh-cn"
            }
        },
        {
            "name": "Custom Event",
            "params": {
                "si": site_id,
                "et": "1",
                "ep": "custom_event",
                "el": "injection_test",
                "ev": "999",
                "st": str(int(time.time()))
            }
        },
        {
            "name": "Minimal Parameters",
            "params": {
                "si": site_id,
                "et": "0",
                "st": str(int(time.time()))
            }
        }
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n[+] Testing: {test['name']}")
        url = f"{ENDPOINT}?{urlencode(test['params'])}"
        print(f"    URL: {url}")
        
        try:
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=False
            )
            
            print(f"    Status: {response.status_code}")
            print(f"    Response Headers: {dict(response.headers)}")
            
            if response.status_code in [401, 403]:
                print("    🔒 Authentication Required")
                results.append({
                    "test": test['name'],
                    "status": response.status_code,
                    "auth_required": True
                })
            elif response.status_code == 200:
                print("    ✅ ACCEPTED!")
                print(f"    Response Size: {len(response.content)} bytes")
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
        print("    Tracking pixel accepts requests")
        print("    Can inject fake analytics data")
    
    return results

if __name__ == "__main__":
    test_baidu_analytics()
