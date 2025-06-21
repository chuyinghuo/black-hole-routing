#!/usr/bin/env python3
"""
Flask Integration Example for IP Guardian
Shows how to integrate IP validation with existing blocklist routes
"""

import asyncio
import sys
import os
from flask import Flask, request, jsonify
from typing import Dict

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the simple IP Guardian
from test_ip_guardian import SimpleIPGuardian

app = Flask(__name__)

# Initialize IP Guardian
guardian = SimpleIPGuardian()

@app.route('/api/validate-ip', methods=['POST'])
def validate_ip():
    """Validate IP address before adding to blocklist"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({'error': 'IP address required'}), 400
        
        # Run async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(guardian.validate_blocklist_addition(ip_address))
        finally:
            loop.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/blocklist-with-validation', methods=['POST'])
def add_ip_with_validation():
    """Add IP to blocklist with Guardian validation"""
    try:
        data = request.get_json()
        ip_address = data.get('ip_address')
        
        if not ip_address:
            return jsonify({'error': 'IP address required'}), 400
        
        # Validate with IP Guardian first
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            validation_result = loop.run_until_complete(guardian.validate_blocklist_addition(ip_address))
        finally:
            loop.close()
        
        # Check if IP should be blocked
        if not validation_result['allowed']:
            return jsonify({
                'error': 'IP blocked by Guardian',
                'reason': validation_result['action'],
                'recommendation': validation_result['recommendation'],
                'risk_level': validation_result['risk_level'],
                'reasons': validation_result['reasons']
            }), 403
        
        # If validation passes, you would call your existing blocklist API here
        # For this example, we'll just return success
        return jsonify({
            'message': 'IP would be added to blocklist',
            'ip_address': ip_address,
            'validation_result': validation_result,
            'status': 'approved'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bulk-validate', methods=['POST'])
def bulk_validate():
    """Validate multiple IPs for bulk operations"""
    try:
        data = request.get_json()
        ip_list = data.get('ip_list', [])
        
        if not ip_list:
            return jsonify({'error': 'IP list required'}), 400
        
        results = {
            'total_ips': len(ip_list),
            'approved': [],
            'blocked': [],
            'summary': {}
        }
        
        # Validate each IP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for ip in ip_list:
                validation = loop.run_until_complete(guardian.validate_blocklist_addition(ip))
                
                if validation['allowed']:
                    results['approved'].append({
                        'ip': ip,
                        'risk_level': validation['risk_level']
                    })
                else:
                    results['blocked'].append({
                        'ip': ip,
                        'reason': validation['action'],
                        'risk_level': validation['risk_level']
                    })
        finally:
            loop.close()
        
        # Generate summary
        results['summary'] = {
            'approved_count': len(results['approved']),
            'blocked_count': len(results['blocked']),
            'safety_score': len(results['approved']) / len(ip_list) if ip_list else 0
        }
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/guardian/stats', methods=['GET'])
def get_guardian_stats():
    """Get IP Guardian statistics"""
    try:
        stats = {
            'service': 'IP Guardian',
            'status': 'active',
            'features': [
                'Critical infrastructure protection',
                'Private network detection',
                'DNS server protection',
                'Large network range analysis',
                'Bulk operation validation'
            ],
            'protected_networks': len(guardian.critical_networks),
            'risk_levels': ['SAFE', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-guardian', methods=['GET'])
def test_guardian():
    """Test endpoint to demonstrate Guardian functionality"""
    
    # Test with some example IPs
    test_ips = [
        '192.168.1.1',    # Should be blocked (private)
        '8.8.8.8',        # Should be blocked (DNS)
        '203.0.113.42',   # Should be allowed (documentation)
        '185.220.101.1'   # Should be allowed (random)
    ]
    
    results = []
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for ip in test_ips:
            validation = loop.run_until_complete(guardian.validate_blocklist_addition(ip))
            results.append({
                'ip': ip,
                'allowed': validation['allowed'],
                'risk_level': validation['risk_level'],
                'recommendation': validation['recommendation']
            })
    finally:
        loop.close()
    
    return jsonify({
        'test_results': results,
        'summary': f'Guardian tested {len(test_ips)} IPs',
        'blocked_count': len([r for r in results if not r['allowed']]),
        'approved_count': len([r for r in results if r['allowed']])
    })

# Example of how to modify existing blocklist route
def enhanced_blocklist_route():
    """
    Example of how to enhance your existing blocklist route with Guardian validation.
    This would replace or wrap your existing POST /blocklist/ route.
    """
    
    # This is pseudocode showing the integration pattern:
    """
    @app.route('/blocklist/', methods=['POST'])
    def add_to_blocklist():
        data = request.get_json()
        ip_address = data.get('ip_address')
        
        # 1. Validate with IP Guardian
        validation = guardian.validate_blocklist_addition(ip_address)
        
        # 2. Check if Guardian allows the block
        if not validation['allowed']:
            return jsonify({
                'error': f"Guardian prevented block: {validation['recommendation']}",
                'guardian_result': validation
            }), 403
        
        # 3. If Guardian approves, proceed with existing logic
        # ... your existing blocklist addition code here ...
        
        # 4. Return success with Guardian info
        return jsonify({
            'message': 'IP added successfully',
            'guardian_validation': validation
        }), 201
    """
    pass

if __name__ == '__main__':
    print("🛡️ Starting Flask IP Guardian Integration Example")
    print("Available endpoints:")
    print("  POST /api/validate-ip           - Validate single IP")
    print("  POST /api/blocklist-with-validation - Add IP with validation")
    print("  POST /api/bulk-validate         - Validate multiple IPs")
    print("  GET  /api/guardian/stats        - Guardian statistics")
    print("  GET  /test-guardian             - Test Guardian functionality")
    print()
    print("Example usage:")
    print("  curl -X POST http://localhost:5002/api/validate-ip \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"ip_address\": \"8.8.8.8\"}'")
    print()
    print("Running on http://localhost:5002")
    
    app.run(debug=True, port=5002)