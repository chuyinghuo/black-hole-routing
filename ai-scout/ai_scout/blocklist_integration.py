"""
Blocklist Integration Module
Integrates IP Guardian agent with the existing Flask blocklist system
"""

import asyncio
import sys
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging
from flask import Flask, request, jsonify
import requests
from ip_guardian import IPGuardianAgent, RiskLevel

# Add parent directories to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../api')))

logger = logging.getLogger(__name__)

class BlocklistGuardian:
    """Middleware that intercepts blocklist operations and validates them with IP Guardian"""
    
    def __init__(self, flask_api_url: str = "http://localhost:5001"):
        self.guardian = IPGuardianAgent()
        self.flask_api_url = flask_api_url
        self.validation_enabled = True
        self.auto_block_threshold = RiskLevel.MEDIUM  # Only auto-block if risk is medium or lower
        
    async def validate_ip_addition(self, ip_address: str, context: Dict = None) -> Dict:
        """Validate IP address before adding to blocklist"""
        try:
            # Get AI analysis
            validation_result = await self.guardian.validate_blocklist_addition(ip_address, context)
            
            # Add integration-specific logic
            integration_result = {
                **validation_result,
                "integration_status": "processed",
                "auto_blocked": False,
                "requires_approval": False,
                "notification_sent": False
            }
            
            # Determine action based on risk level
            risk_level = RiskLevel(validation_result["risk_level"])
            
            if risk_level == RiskLevel.CRITICAL:
                integration_result["action"] = "BLOCKED"
                integration_result["message"] = "❌ IP addition BLOCKED - Critical infrastructure risk detected"
                await self._send_critical_alert(validation_result)
                
            elif risk_level == RiskLevel.HIGH:
                integration_result["action"] = "PENDING_APPROVAL"
                integration_result["requires_approval"] = True
                integration_result["message"] = "⚠️ IP addition requires MANUAL APPROVAL - High risk detected"
                await self._send_approval_request(validation_result)
                
            elif risk_level == RiskLevel.MEDIUM:
                integration_result["action"] = "PROCEED_WITH_CAUTION"
                integration_result["message"] = "🔶 IP addition allowed with WARNING - Monitor for impact"
                await self._send_caution_notification(validation_result)
                
            else:  # LOW or SAFE
                integration_result["action"] = "APPROVED"
                integration_result["auto_blocked"] = True
                integration_result["message"] = "✅ IP addition approved - Safe to block"
            
            return integration_result
            
        except Exception as e:
            logger.error(f"Error validating IP {ip_address}: {str(e)}")
            return {
                "ip_address": ip_address,
                "action": "ERROR",
                "message": f"Validation failed: {str(e)}",
                "integration_status": "error"
            }
    
    async def validate_bulk_operation(self, ip_list: List[str]) -> Dict:
        """Validate bulk IP operations"""
        results = {
            "total_ips": len(ip_list),
            "approved": [],
            "blocked": [],
            "pending_approval": [],
            "errors": [],
            "summary": {}
        }
        
        # Add bulk operation context
        context = {
            "bulk_operation": True,
            "total_count": len(ip_list),
            "automated": True
        }
        
        for ip_address in ip_list:
            try:
                validation = await self.validate_ip_addition(ip_address, context)
                
                if validation["action"] == "APPROVED":
                    results["approved"].append(validation)
                elif validation["action"] == "BLOCKED":
                    results["blocked"].append(validation)
                elif validation["action"] == "PENDING_APPROVAL":
                    results["pending_approval"].append(validation)
                else:
                    results["errors"].append(validation)
                    
            except Exception as e:
                results["errors"].append({
                    "ip_address": ip_address,
                    "error": str(e)
                })
        
        # Generate summary
        results["summary"] = {
            "approved_count": len(results["approved"]),
            "blocked_count": len(results["blocked"]),
            "pending_count": len(results["pending_approval"]),
            "error_count": len(results["errors"]),
            "safety_score": self._calculate_safety_score(results)
        }
        
        # Send bulk operation summary
        if results["blocked"] or results["pending_approval"]:
            await self._send_bulk_operation_alert(results)
        
        return results
    
    def _calculate_safety_score(self, results: Dict) -> float:
        """Calculate overall safety score for bulk operation"""
        total = results["total_ips"]
        if total == 0:
            return 1.0
        
        blocked = len(results["blocked"])
        pending = len(results["pending_approval"])
        
        # Higher score means safer operation
        safety_score = 1.0 - ((blocked * 1.0 + pending * 0.5) / total)
        return max(0.0, min(1.0, safety_score))
    
    async def _send_critical_alert(self, validation_result: Dict):
        """Send critical alert for dangerous IP blocking attempts"""
        alert = {
            "type": "CRITICAL_IP_BLOCK_PREVENTED",
            "ip_address": validation_result["ip_address"],
            "reasons": validation_result["reasons"],
            "recommendation": validation_result["recommendation"],
            "timestamp": datetime.now().isoformat(),
            "action_required": False  # Already blocked
        }
        
        logger.critical(f"CRITICAL ALERT: Prevented dangerous IP block: {alert}")
        # In production, send to Slack/Teams/email
        await self._send_notification(alert, priority="critical")
    
    async def _send_approval_request(self, validation_result: Dict):
        """Send approval request for high-risk IP blocks"""
        request_data = {
            "type": "IP_BLOCK_APPROVAL_REQUEST",
            "ip_address": validation_result["ip_address"],
            "reasons": validation_result["reasons"],
            "recommendation": validation_result["recommendation"],
            "timestamp": datetime.now().isoformat(),
            "action_required": True,
            "approval_url": f"{self.flask_api_url}/api/approve-block/{validation_result['ip_address']}"
        }
        
        logger.warning(f"APPROVAL REQUIRED: High-risk IP block: {request_data}")
        await self._send_notification(request_data, priority="high")
    
    async def _send_caution_notification(self, validation_result: Dict):
        """Send caution notification for medium-risk blocks"""
        notification = {
            "type": "IP_BLOCK_CAUTION",
            "ip_address": validation_result["ip_address"],
            "recommendation": validation_result["recommendation"],
            "timestamp": datetime.now().isoformat(),
            "monitor_required": True
        }
        
        logger.info(f"CAUTION: Medium-risk IP block proceeded: {notification}")
        await self._send_notification(notification, priority="medium")
    
    async def _send_bulk_operation_alert(self, results: Dict):
        """Send alert for bulk operations with blocked/pending IPs"""
        alert = {
            "type": "BULK_OPERATION_ALERT",
            "total_ips": results["total_ips"],
            "blocked_count": results["summary"]["blocked_count"],
            "pending_count": results["summary"]["pending_count"],
            "safety_score": results["summary"]["safety_score"],
            "timestamp": datetime.now().isoformat(),
            "blocked_ips": [ip["ip_address"] for ip in results["blocked"][:5]],  # First 5
            "pending_ips": [ip["ip_address"] for ip in results["pending_approval"][:5]]  # First 5
        }
        
        logger.warning(f"BULK OPERATION ALERT: {alert}")
        await self._send_notification(alert, priority="high")
    
    async def _send_notification(self, data: Dict, priority: str = "medium"):
        """Send notification via configured channels"""
        # Placeholder for notification system
        # In production, integrate with Slack, Teams, email, etc.
        
        if priority == "critical":
            # Immediate notification
            print(f"🚨 CRITICAL ALERT: {data}")
        elif priority == "high":
            # High priority notification
            print(f"⚠️ HIGH PRIORITY: {data}")
        else:
            # Standard notification
            print(f"ℹ️ NOTIFICATION: {data}")
    
    async def create_approval_workflow(self, ip_address: str, validation_result: Dict) -> Dict:
        """Create approval workflow for high-risk IP blocks"""
        workflow = {
            "id": f"approval_{ip_address}_{int(datetime.now().timestamp())}",
            "ip_address": ip_address,
            "validation_result": validation_result,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "approver": None,
            "approved_at": None,
            "expiry": (datetime.now()).isoformat()  # 24 hour expiry
        }
        
        # Store in database or cache
        await self._store_approval_workflow(workflow)
        
        return workflow
    
    async def _store_approval_workflow(self, workflow: Dict):
        """Store approval workflow in database"""
        # Implementation would store in database
        # For now, just log it
        logger.info(f"Stored approval workflow: {workflow['id']}")
    
    async def get_guardian_statistics(self) -> Dict:
        """Get IP Guardian statistics and metrics"""
        stats = await self.guardian.get_validation_stats()
        
        # Add integration-specific metrics
        integration_stats = {
            **stats,
            "integration_metrics": {
                "validation_enabled": self.validation_enabled,
                "auto_block_threshold": self.auto_block_threshold.value,
                "flask_api_url": self.flask_api_url,
                "uptime": "active"  # Could track actual uptime
            }
        }
        
        return integration_stats

# Flask extension for easy integration
class FlaskIPGuardian:
    """Flask extension for IP Guardian integration"""
    
    def __init__(self, app: Flask = None):
        self.app = app
        self.guardian = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the extension with Flask app"""
        self.app = app
        self.guardian = BlocklistGuardian()
        
        # Add routes for IP validation
        self._add_routes()
        
        # Add before_request hook for automatic validation
        app.before_request(self._before_request_handler)
    
    def _add_routes(self):
        """Add IP Guardian routes to Flask app"""
        
        @self.app.route('/api/guardian/validate', methods=['POST'])
        async def validate_ip():
            """Endpoint to validate IP before blocking"""
            data = request.get_json()
            ip_address = data.get('ip_address')
            context = data.get('context', {})
            
            if not ip_address:
                return jsonify({'error': 'IP address required'}), 400
            
            result = await self.guardian.validate_ip_addition(ip_address, context)
            return jsonify(result)
        
        @self.app.route('/api/guardian/validate-bulk', methods=['POST'])
        async def validate_bulk():
            """Endpoint to validate bulk IP operations"""
            data = request.get_json()
            ip_list = data.get('ip_list', [])
            
            if not ip_list:
                return jsonify({'error': 'IP list required'}), 400
            
            result = await self.guardian.validate_bulk_operation(ip_list)
            return jsonify(result)
        
        @self.app.route('/api/guardian/stats', methods=['GET'])
        async def get_stats():
            """Endpoint to get IP Guardian statistics"""
            stats = await self.guardian.get_guardian_statistics()
            return jsonify(stats)
    
    def _before_request_handler(self):
        """Handle requests to blocklist endpoints"""
        if request.endpoint and 'blocklist' in request.endpoint:
            # Add validation logic here if needed
            pass

# Example usage function
async def test_integration():
    """Test the blocklist integration"""
    guardian = BlocklistGuardian()
    
    # Test dangerous IPs
    dangerous_ips = [
        "192.168.1.1",    # Private network
        "8.8.8.8",        # Google DNS
        "127.0.0.1",      # Localhost
        "10.0.0.0/8",     # Large private network
    ]
    
    print("🛡️ Testing IP Guardian Integration")
    print("=" * 50)
    
    for ip in dangerous_ips:
        result = await guardian.validate_ip_addition(ip)
        print(f"\n📍 IP: {ip}")
        print(f"   Action: {result['action']}")
        print(f"   Message: {result['message']}")
        print(f"   Risk Level: {result['risk_level']}")
    
    # Test bulk operation
    print(f"\n📦 Testing Bulk Operation")
    bulk_result = await guardian.validate_bulk_operation(dangerous_ips)
    print(f"   Total IPs: {bulk_result['total_ips']}")
    print(f"   Approved: {bulk_result['summary']['approved_count']}")
    print(f"   Blocked: {bulk_result['summary']['blocked_count']}")
    print(f"   Safety Score: {bulk_result['summary']['safety_score']:.2f}")

if __name__ == "__main__":
    asyncio.run(test_integration())