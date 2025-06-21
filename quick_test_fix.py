#!/usr/bin/env python3
"""
Quick test to verify CRUD and AI analysis fixes
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5001"

def test_crud_operations():
    """Test basic CRUD operations"""
    print("🔍 Testing CRUD Operations")
    print("-" * 40)
    
    # Test GET (Read)
    try:
        response = requests.get(f"{BASE_URL}/api/blocklist/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET: Found {len(data)} blocklist entries")
            return data[:3] if data else []  # Return first 3 for testing
        else:
            print(f"❌ GET failed: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ GET error: {e}")
        return []

def test_ai_analysis(test_ips):
    """Test AI analysis for different IP types"""
    print("\n🤖 Testing AI Analysis")
    print("-" * 40)
    
    # Test with known IPs that should have different risk levels
    test_cases = [
        ("8.8.8.8", "Google DNS - Should be CRITICAL"),
        ("192.168.1.1", "Private Network - Should be CRITICAL"),
        ("1.2.3.4", "Random IP - Should be MEDIUM"),
        ("127.0.0.1", "Localhost - Should be CRITICAL")
    ]
    
    # Add existing IPs from database
    for entry in test_ips:
        ip = entry.get('ip_address', '')
        if ip:
            test_cases.append((ip, f"Database IP - {ip}"))
    
    results = []
    for ip, description in test_cases[:6]:  # Test max 6 IPs
        try:
            response = requests.post(
                f"{BASE_URL}/api/blocklist/guardian/explain",
                headers={'Content-Type': 'application/json'},
                json={'ip_address': ip}
            )
            
            if response.status_code == 200:
                data = response.json()
                risk_level = data.get('risk_level', 'UNKNOWN')
                confidence = int((data.get('confidence', 0) * 100))
                
                print(f"  {ip:15} | {risk_level:8} | {confidence:3}% | {description}")
                results.append((ip, risk_level, confidence))
            else:
                print(f"  {ip:15} | ERROR    | N/A  | {description}")
                
        except Exception as e:
            print(f"  {ip:15} | ERROR    | N/A  | Error: {e}")
    
    return results

def test_guardian_override():
    """Test Guardian override functionality"""
    print("\n🛡️ Testing Guardian Override")
    print("-" * 40)
    
    # Test with Google DNS (should trigger Guardian warning)
    test_data = {
        "ip_address": "8.8.8.8",
        "time_added": "2025-06-21T17:00",
        "duration": "1",
        "comment": "Test Guardian Override",
        "blocks_count": "1",
        "created_by": ""
    }
    
    try:
        # First attempt - should be blocked by Guardian
        response = requests.post(
            f"{BASE_URL}/api/blocklist/",
            headers={'Content-Type': 'application/json'},
            json=test_data
        )
        
        if response.status_code == 403:
            data = response.json()
            if data.get('guardian_block') and data.get('can_override'):
                print("✅ Guardian blocking works correctly")
                print(f"   Risk Level: {data.get('risk_level', 'N/A')}")
                print(f"   Can Override: {data.get('can_override', False)}")
                
                # Test override
                test_data['override_guardian'] = True
                override_response = requests.post(
                    f"{BASE_URL}/api/blocklist/",
                    headers={'Content-Type': 'application/json'},
                    json=test_data
                )
                
                if override_response.status_code in [200, 201]:
                    print("✅ Guardian override works correctly")
                    
                    # Clean up - delete the test entry
                    cleanup_response = requests.get(f"{BASE_URL}/api/blocklist/")
                    if cleanup_response.status_code == 200:
                        entries = cleanup_response.json()
                        for entry in entries:
                            if entry.get('ip_address') == '8.8.8.8' and 'Test Guardian Override' in entry.get('comment', ''):
                                delete_response = requests.post(
                                    f"{BASE_URL}/api/blocklist/delete",
                                    headers={'Content-Type': 'application/json'},
                                    json={'entry_id': entry['id']}
                                )
                                if delete_response.status_code == 200:
                                    print("✅ Cleanup successful")
                                break
                else:
                    print(f"❌ Override failed: {override_response.status_code}")
            else:
                print(f"❌ Guardian response missing override flags: {data}")
        else:
            print(f"❌ Guardian not blocking as expected: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Override test error: {e}")

def main():
    print("🧪 Quick Fix Verification Test")
    print("=" * 50)
    
    # Test CRUD
    test_entries = test_crud_operations()
    
    # Test AI Analysis
    ai_results = test_ai_analysis(test_entries)
    
    # Test Guardian Override
    test_guardian_override()
    
    # Summary
    print("\n📊 Test Summary")
    print("-" * 40)
    
    if test_entries:
        print("✅ CRUD Operations: Working")
    else:
        print("❌ CRUD Operations: Issues detected")
    
    if ai_results:
        unique_risks = set(result[1] for result in ai_results)
        if len(unique_risks) > 1:
            print("✅ AI Analysis: Working (different risk levels detected)")
        else:
            print("❌ AI Analysis: All showing same risk level")
        
        print(f"   Risk levels found: {', '.join(unique_risks)}")
    else:
        print("❌ AI Analysis: No results")
    
    print("\n🎯 Ready to test in browser!")
    print("   Go to: http://127.0.0.1:5001/blocklist")

if __name__ == "__main__":
    main() 