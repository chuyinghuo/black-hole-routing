#!/usr/bin/env python3
"""
Test script to verify AI analysis is working correctly through the web interface
"""

import requests
import json

def test_ai_analysis_web():
    """Test AI analysis through the web API"""
    base_url = "http://127.0.0.1:5001"
    
    # Test cases with expected risk levels
    test_cases = [
        ("8.8.8.8", "critical", "Google DNS"),
        ("1.1.1.1", "critical", "Cloudflare DNS"), 
        ("192.168.1.1", "critical", "Private Network"),
        ("127.0.0.1", "critical", "Localhost"),
        ("1.2.3.4", "medium", "Random IP"),
        ("10.0.0.1", "critical", "Private Network")
    ]
    
    print("🧪 Testing AI Analysis Web Interface")
    print("=" * 50)
    
    # Check Guardian status first
    try:
        response = requests.get(f"{base_url}/api/blocklist/guardian/status")
        if response.status_code == 200:
            status = response.json()
            print(f"Guardian Status: Available={status['available']}, Enabled={status['enabled']}, Initialized={status['guardian_initialized']}")
        else:
            print(f"❌ Failed to get Guardian status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error checking Guardian status: {e}")
        return
    
    print("\n🤖 Testing AI Analysis Endpoint")
    print("-" * 40)
    print(f"{'IP Address':<15} | {'Expected':<8} | {'Actual':<8} | {'Confidence':<10} | {'Status'}")
    print("-" * 70)
    
    all_passed = True
    
    for ip, expected_risk, description in test_cases:
        try:
            response = requests.post(
                f"{base_url}/api/blocklist/guardian/explain",
                headers={'Content-Type': 'application/json'},
                json={'ip_address': ip}
            )
            
            if response.status_code == 200:
                data = response.json()
                actual_risk = data.get('risk_level', 'UNKNOWN')
                confidence = int((data.get('confidence', 0) * 100))
                
                status = "✅ PASS" if actual_risk == expected_risk else "❌ FAIL"
                if actual_risk != expected_risk:
                    all_passed = False
                
                print(f"{ip:<15} | {expected_risk:<8} | {actual_risk:<8} | {confidence:>3}%      | {status}")
                
                # Show detailed explanation for first test
                if ip == "8.8.8.8":
                    print(f"\n📋 Sample AI Explanation for {ip}:")
                    explanation = data.get('detailed_explanation', 'No explanation available')
                    # Show first few lines of explanation
                    lines = explanation.split('\n')[:5]
                    for line in lines:
                        print(f"    {line}")
                    print("    ...")
                    print()
                    
            else:
                print(f"{ip:<15} | {expected_risk:<8} | ERROR    | N/A       | ❌ HTTP {response.status_code}")
                all_passed = False
                
        except Exception as e:
            print(f"{ip:<15} | {expected_risk:<8} | ERROR    | N/A       | ❌ {str(e)[:20]}")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED! AI Analysis is working correctly.")
        print("✅ The frontend should now show proper risk levels instead of UNKNOWN.")
        print(f"🌐 Access the application at: {base_url}/blocklist")
    else:
        print("❌ Some tests failed. Check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    test_ai_analysis_web() 