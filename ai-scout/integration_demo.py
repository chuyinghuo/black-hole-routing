#!/usr/bin/env python3
"""
IP Guardian Integration Demo
Shows how to integrate with existing Flask blocklist system
"""

import asyncio
import json
from typing import Optional
from test_ip_guardian import SimpleIPGuardian

class BlocklistIntegration:
    """Demonstration of IP Guardian integration with blocklist system"""
    
    def __init__(self):
        self.guardian = SimpleIPGuardian()
        self.blocked_ips = []  # Simulated blocklist
        self.prevented_blocks = []  # IPs that Guardian prevented
        
    async def safe_add_to_blocklist(self, ip_address: str, context: Optional[dict] = None) -> dict:
        """Safely add IP to blocklist with Guardian validation"""
        
        print(f"🔍 Attempting to block IP: {ip_address}")
        
        # Step 1: Validate with IP Guardian
        validation = await self.guardian.validate_blocklist_addition(ip_address, context or {})
        
        result = {
            'ip_address': ip_address,
            'timestamp': validation['analysis_time'],
            'guardian_validation': validation
        }
        
        # Step 2: Act based on Guardian recommendation
        if not validation['allowed']:
            # Guardian prevented the block
            self.prevented_blocks.append(ip_address)
            result['status'] = 'BLOCKED_BY_GUARDIAN'
            result['message'] = f"❌ Guardian prevented block: {validation['recommendation']}"
            
            print(f"    🛡️ BLOCKED BY GUARDIAN: {validation['recommendation']}")
            
        else:
            # Guardian approved the block
            self.blocked_ips.append(ip_address)
            result['status'] = 'ADDED_TO_BLOCKLIST'
            result['message'] = f"✅ IP added to blocklist: {validation['recommendation']}"
            
            print(f"    ✅ APPROVED: {validation['recommendation']}")
        
        return result
    
    async def bulk_block_with_validation(self, ip_list: list) -> dict:
        """Perform bulk blocking operation with Guardian validation"""
        
        print(f"\n🔄 Bulk operation: Attempting to block {len(ip_list)} IPs")
        
        results = {
            'total_ips': len(ip_list),
            'successful_blocks': [],
            'guardian_prevented': [],
            'errors': []
        }
        
        for ip in ip_list:
            try:
                result = await self.safe_add_to_blocklist(ip)
                
                if result['status'] == 'ADDED_TO_BLOCKLIST':
                    results['successful_blocks'].append(ip)
                elif result['status'] == 'BLOCKED_BY_GUARDIAN':
                    results['guardian_prevented'].append({
                        'ip': ip,
                        'reason': result['guardian_validation']['action'],
                        'risk_level': result['guardian_validation']['risk_level']
                    })
                    
            except Exception as e:
                results['errors'].append({'ip': ip, 'error': str(e)})
        
        # Calculate safety metrics
        total = len(ip_list)
        blocked_count = len(results['guardian_prevented'])
        success_count = len(results['successful_blocks'])
        
        results['summary'] = {
            'success_rate': success_count / total if total > 0 else 0,
            'guardian_prevention_rate': blocked_count / total if total > 0 else 0,
            'dangerous_blocks_prevented': blocked_count
        }
        
        return results
    
    def get_system_status(self) -> dict:
        """Get current system status and statistics"""
        return {
            'guardian_status': 'active',
            'total_blocked_ips': len(self.blocked_ips),
            'dangerous_blocks_prevented': len(self.prevented_blocks),
            'prevented_ips': self.prevented_blocks,
            'safety_features': [
                'Critical infrastructure protection',
                'Private network detection', 
                'DNS server protection',
                'Large network analysis',
                'Real-time validation'
            ]
        }

async def demonstrate_integration():
    """Demonstrate the integration in action"""
    
    integration = BlocklistIntegration()
    
    print("🛡️ IP Guardian Integration Demonstration")
    print("=" * 60)
    print("This shows how the IP Guardian protects your blocklist system\n")
    
    # Test 1: Individual IP additions
    print("📍 Test 1: Individual IP Additions")
    print("-" * 40)
    
    dangerous_ips = [
        "192.168.1.100",   # Private network
        "8.8.8.8",         # Google DNS
        "127.0.0.1",       # Localhost
    ]
    
    safe_ips = [
        "203.0.113.42",    # Documentation range
        "185.220.101.1",   # Random suspicious IP
    ]
    
    # Try to block dangerous IPs (should be prevented)
    for ip in dangerous_ips:
        await integration.safe_add_to_blocklist(ip)
    
    print()
    
    # Try to block safe IPs (should be allowed)
    for ip in safe_ips:
        await integration.safe_add_to_blocklist(ip)
    
    print()
    
    # Test 2: Bulk operation
    print("📦 Test 2: Bulk Operation")
    print("-" * 40)
    
    bulk_ips = [
        "10.0.0.0/24",     # Private subnet - dangerous
        "1.1.1.1",         # Cloudflare DNS - dangerous
        "192.0.2.1",       # Documentation - safe
        "198.51.100.1",    # Test range - safe
        "104.244.74.211",  # Random IP - safe
        "52.0.0.0/16",     # AWS range - dangerous
    ]
    
    bulk_results = await integration.bulk_block_with_validation(bulk_ips)
    
    print(f"\n📊 Bulk Operation Results:")
    print(f"   Total IPs: {bulk_results['total_ips']}")
    print(f"   Successfully blocked: {len(bulk_results['successful_blocks'])}")
    print(f"   Prevented by Guardian: {len(bulk_results['guardian_prevented'])}")
    print(f"   Success rate: {bulk_results['summary']['success_rate']:.1%}")
    print(f"   Guardian prevention rate: {bulk_results['summary']['guardian_prevention_rate']:.1%}")
    
    if bulk_results['guardian_prevented']:
        print(f"\n🛡️ Guardian prevented these dangerous blocks:")
        for item in bulk_results['guardian_prevented']:
            print(f"   • {item['ip']} (Risk: {item['risk_level']})")
    
    # Test 3: System status
    print(f"\n🔧 Test 3: System Status")
    print("-" * 40)
    
    status = integration.get_system_status()
    print(f"Guardian Status: {status['guardian_status']}")
    print(f"Total IPs in blocklist: {status['total_blocked_ips']}")
    print(f"Dangerous blocks prevented: {status['dangerous_blocks_prevented']}")
    
    if status['prevented_ips']:
        print(f"\nPrevented IPs: {', '.join(status['prevented_ips'][:5])}")
    
    print(f"\n✨ Integration Features:")
    for feature in status['safety_features']:
        print(f"   ✓ {feature}")
    
    # Test 4: Real-world scenario
    print(f"\n🌍 Test 4: Real-World Scenario")
    print("-" * 40)
    print("Simulating a scenario where someone accidentally tries to block")
    print("their entire company's IP range...")
    
    company_network = "192.168.0.0/16"  # Entire company network
    result = await integration.safe_add_to_blocklist(
        company_network, 
        context={'source': 'automated', 'bulk_operation': True}
    )
    
    print(f"\nResult: {result['message']}")
    print("💡 The Guardian saved your company from a network outage!")

def show_integration_code_example():
    """Show how to integrate with existing Flask routes"""
    
    print("\n" + "="*60)
    print("🔧 Integration Code Example")
    print("="*60)
    
    code_example = '''
# How to modify your existing blocklist route:

from ai_scout.test_ip_guardian import SimpleIPGuardian

guardian = SimpleIPGuardian()

@blocklist_bp.route("/", methods=["POST"])
async def home():
    if request.method == "POST":
        data = request.get_json() or request.form
        ip_address = data.get("ip_address")
        
        # 🛡️ ADD GUARDIAN VALIDATION HERE
        validation = await guardian.validate_blocklist_addition(ip_address)
        
        if not validation['allowed']:
            return jsonify({
                'error': 'Guardian prevented block',
                'reason': validation['recommendation'],
                'risk_level': validation['risk_level'],
                'guardian_details': validation
            }), 403
        
        # ✅ If Guardian approves, proceed with existing logic
        # ... your existing blocklist code here ...
        
        return jsonify({
            'message': 'IP added successfully',
            'guardian_approved': True,
            'validation': validation
        }), 201
    '''
    
    print(code_example)

if __name__ == "__main__":
    print("🚀 Starting IP Guardian Integration Demo...\n")
    asyncio.run(demonstrate_integration())
    show_integration_code_example()
    print("\n🎉 Demo completed! The IP Guardian is ready to protect your blocklist system.") 