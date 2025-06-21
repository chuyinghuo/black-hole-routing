#!/usr/bin/env python3
"""
Test script to verify the frontend AI analysis is working correctly
"""

import requests
import json

def test_frontend_ai():
    """Test the frontend AI analysis functionality"""
    base_url = "http://127.0.0.1:5001"
    
    print("🌐 Testing Frontend AI Analysis")
    print("=" * 50)
    
    # Test cases
    test_ips = ["8.8.8.8", "1.1.1.1", "192.168.1.1", "1.2.3.4"]
    
    print("Testing AI Analysis endpoint that frontend uses:")
    print("-" * 50)
    
    for ip in test_ips:
        try:
            response = requests.post(
                f"{base_url}/api/blocklist/guardian/explain",
                headers={'Content-Type': 'application/json'},
                json={'ip_address': ip}
            )
            
            if response.status_code == 200:
                data = response.json()
                risk_level = data.get('risk_level', 'UNKNOWN')
                confidence = int((data.get('confidence', 0) * 100))
                guardian_enabled = data.get('guardian_enabled', False)
                
                status = "✅" if risk_level != 'UNKNOWN' else "❌"
                print(f"{status} {ip:<15} | Risk: {risk_level:<8} | Confidence: {confidence:>3}% | Guardian: {guardian_enabled}")
                
                if risk_level == 'UNKNOWN':
                    print(f"   ⚠️  Explanation: {data.get('detailed_explanation', 'No explanation')[:100]}...")
                
            else:
                print(f"❌ {ip:<15} | HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {ip:<15} | Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎯 Instructions for testing in browser:")
    print(f"1. Go to: {base_url}/blocklist")
    print("2. Click 'AI Analysis' button on any IP")
    print("3. You should see risk levels like CRITICAL, MEDIUM, etc.")
    print("4. If you see UNKNOWN, check Guardian status in the UI")
    
    # Test Guardian status
    print(f"\n🛡️  Current Guardian Status:")
    try:
        response = requests.get(f"{base_url}/api/blocklist/guardian/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   Available: {status['available']}")
            print(f"   Enabled: {status['enabled']}")
            print(f"   Initialized: {status['guardian_initialized']}")
        else:
            print(f"   Error getting status: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")

if __name__ == "__main__":
    test_frontend_ai()
