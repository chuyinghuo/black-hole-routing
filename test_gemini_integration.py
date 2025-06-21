#!/usr/bin/env python3
"""
Test script for Gemini NLP Integration
Run this after setting your API_KEY environment variable
"""

import asyncio
import os
import sys

# Add the ai-scout directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai-scout'))

from ai_scout.ip_guardian import IPGuardianAgent

def check_api_key():
    """Check if API key is configured"""
    api_key = os.getenv('API_KEY') or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ No API key found!")
        print("\nTo use Gemini NLP, please set your API key:")
        print("export API_KEY='your-gemini-api-key-here'")
        print("\nGet a free API key from: https://makersuite.google.com/app/apikey")
        print("\nNote: The system will still work with enhanced local explanations without the API key.")
        return False
    else:
        print(f"✅ API key found (length: {len(api_key)} characters)")
        return True

async def test_with_gemini():
    """Test IP Guardian with Gemini NLP integration"""
    
    print("🤖 Testing IP Guardian with Gemini NLP Integration")
    print("=" * 60)
    
    # Check API key
    has_api_key = check_api_key()
    print()
    
    # Initialize Guardian
    guardian = IPGuardianAgent()
    
    # Test cases
    test_ips = [
        ("8.8.8.8", "Google DNS - Critical Infrastructure"),
        ("192.168.1.1", "Private Network Address"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("52.86.25.100", "AWS Cloud Server"),
        ("198.51.100.42", "Documentation IP Range")
    ]
    
    for ip, description in test_ips:
        print(f"\n🔍 Analyzing: {ip} ({description})")
        print("-" * 50)
        
        try:
            result = await guardian.validate_blocklist_addition(ip)
            
            print(f"📊 Risk Level: {result['risk_level'].upper()}")
            print(f"🎯 Confidence: {result['confidence']:.1%}")
            print(f"🔒 Action: {'BLOCKED' if not result['allowed'] else 'ALLOWED'}")
            
            # Show explanation preview
            explanation = result.get('recommendation', 'No explanation available')
            
            if has_api_key and guardian.gemini_explainer and guardian.gemini_explainer.is_available():
                print(f"\n🧠 Gemini-Powered Explanation:")
                # Show first 400 characters of the explanation
                print(explanation[:400] + "..." if len(explanation) > 400 else explanation)
            else:
                print(f"\n📝 Standard Explanation:")
                # Show first 300 characters for standard explanation
                print(explanation[:300] + "..." if len(explanation) > 300 else explanation)
                
        except Exception as e:
            print(f"❌ Error analyzing {ip}: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("🎯 Test Complete!")
    
    if has_api_key:
        if guardian.gemini_explainer and guardian.gemini_explainer.is_available():
            print("✅ Gemini NLP: ACTIVE - Enhanced AI explanations provided")
        else:
            print("⚠️ Gemini NLP: ERROR - Check API key validity")
    else:
        print("📝 Standard Mode: Enhanced local explanations (set API_KEY for Gemini)")
    
    print(f"📈 Guardian Status: {'OPERATIONAL' if guardian else 'ERROR'}")

def main():
    """Main function"""
    try:
        # Run the async test
        asyncio.run(test_with_gemini())
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 