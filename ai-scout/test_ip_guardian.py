#!/usr/bin/env python3
"""
Standalone test script for IP Guardian Agent
Demonstrates IP validation and threat detection without external dependencies
"""

import asyncio
import ipaddress
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class IPAnalysis:
    ip_address: str
    risk_level: RiskLevel
    confidence: float
    reasons: List[str]
    suggested_action: str
    analysis_time: datetime
    network_info: Optional[Dict] = None

class SimpleIPGuardian:
    """Simplified IP Guardian for demonstration"""
    
    def __init__(self):
        self.critical_networks = self._load_critical_networks()
        self.blocked_count_threshold = 1000
        
    def _load_critical_networks(self) -> Set[str]:
        """Load known critical network ranges"""
        return {
            # Private networks (RFC 1918)
            "10.0.0.0/8",
            "172.16.0.0/12", 
            "192.168.0.0/16",
            
            # Loopback
            "127.0.0.0/8",
            "::1/128",
            
            # Link-local
            "169.254.0.0/16",
            "fe80::/10",
            
            # Major DNS providers
            "8.8.8.0/24",      # Google DNS
            "1.1.1.0/24",      # Cloudflare DNS
            
            # Major cloud providers (examples)
            "52.0.0.0/8",      # AWS
            "104.16.0.0/12",   # Cloudflare
            
            # GitHub
            "140.82.112.0/20",
            
            # Documentation ranges (safe to block)
            "192.0.2.0/24",    # TEST-NET-1
            "198.51.100.0/24", # TEST-NET-2
            "203.0.113.0/24",  # TEST-NET-3
        }
    
    async def analyze_ip(self, ip_address: str, context: Dict = None) -> IPAnalysis:
        """Analyze IP address for blocking risks"""
        try:
            # Parse IP address
            try:
                ip_obj = ipaddress.ip_network(ip_address, strict=False)
            except ValueError as e:
                return IPAnalysis(
                    ip_address=ip_address,
                    risk_level=RiskLevel.CRITICAL,
                    confidence=1.0,
                    reasons=[f"Invalid IP format: {str(e)}"],
                    suggested_action="REJECT - Invalid IP format",
                    analysis_time=datetime.now()
                )
            
            reasons = []
            risk_factors = []
            
            # 1. Critical Network Check
            critical_risk = self._check_critical_networks(ip_obj)
            if critical_risk:
                reasons.extend(critical_risk)
                risk_factors.append(0.95)
            
            # 2. Network Size Analysis
            size_risk = self._analyze_network_size(ip_obj)
            if size_risk:
                reasons.extend(size_risk["reasons"])
                risk_factors.append(size_risk["risk_score"])
            
            # 3. Special IP Analysis
            special_risk = self._analyze_special_ips(str(ip_obj.network_address))
            if special_risk:
                reasons.extend(special_risk["reasons"])
                risk_factors.append(special_risk["risk_score"])
            
            # Calculate overall risk
            overall_risk_score = max(risk_factors) if risk_factors else 0.1
            confidence = min(len(risk_factors) * 0.2 + 0.6, 1.0)
            
            # Determine risk level and action
            risk_level, suggested_action = self._determine_risk_level(overall_risk_score, reasons)
            
            return IPAnalysis(
                ip_address=ip_address,
                risk_level=risk_level,
                confidence=confidence,
                reasons=reasons,
                suggested_action=suggested_action,
                analysis_time=datetime.now(),
                network_info={"size": ip_obj.num_addresses, "network": str(ip_obj)}
            )
            
        except Exception as e:
            logger.error(f"Error analyzing IP {ip_address}: {str(e)}")
            return IPAnalysis(
                ip_address=ip_address,
                risk_level=RiskLevel.MEDIUM,
                confidence=0.5,
                reasons=[f"Analysis error: {str(e)}"],
                suggested_action="MANUAL_REVIEW - Analysis failed",
                analysis_time=datetime.now()
            )
    
    def _check_critical_networks(self, ip_obj) -> List[str]:
        """Check if IP overlaps with critical networks"""
        reasons = []
        
        for critical_network in self.critical_networks:
            try:
                critical_net = ipaddress.ip_network(critical_network)
                if ip_obj.overlaps(critical_net):
                    # Check if it's a documentation range (safe to block)
                    if str(critical_net).startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
                        continue  # These are safe to block
                    
                    reasons.append(f"CRITICAL: Overlaps with essential network {critical_network}")
                    
                    # Additional specific checks
                    if str(critical_net).startswith("127."):
                        reasons.append("CRITICAL: Localhost/loopback - would break local services")
                    elif str(critical_net).startswith(("10.", "172.16.", "192.168.")):
                        reasons.append("CRITICAL: Private network - would block internal infrastructure")
                    elif "8.8.8" in str(critical_net):
                        reasons.append("CRITICAL: Google DNS - would break internet connectivity")
                    elif "1.1.1" in str(critical_net):
                        reasons.append("CRITICAL: Cloudflare DNS - would break internet connectivity")
                    elif "140.82.112" in str(critical_net):
                        reasons.append("HIGH RISK: GitHub infrastructure")
                        
            except ValueError:
                continue
                
        return reasons
    
    def _analyze_network_size(self, ip_obj) -> Optional[Dict]:
        """Analyze network size for blocking impact"""
        num_addresses = ip_obj.num_addresses
        
        if num_addresses == 1:
            return None  # Single IP is generally safe
        
        reasons = []
        risk_score = 0.0
        
        if num_addresses > 16777216:  # /8 network
            reasons.append(f"CRITICAL: Entire /8 network ({num_addresses:,} addresses)")
            risk_score = 0.95
        elif num_addresses > 1048576:  # /12 network
            reasons.append(f"HIGH RISK: Large /12 network ({num_addresses:,} addresses)")
            risk_score = 0.85
        elif num_addresses > 65536:  # /16 network
            reasons.append(f"MEDIUM RISK: /16 network ({num_addresses:,} addresses)")
            risk_score = 0.65
        elif num_addresses > 256:  # /24 network
            reasons.append(f"LOW RISK: /24 network ({num_addresses:,} addresses)")
            risk_score = 0.35
        
        if num_addresses > self.blocked_count_threshold:
            reasons.append(f"WARNING: Would block {num_addresses:,} IP addresses")
            risk_score = max(risk_score, 0.7)
        
        return {"reasons": reasons, "risk_score": risk_score} if reasons else None
    
    def _analyze_special_ips(self, ip_address: str) -> Optional[Dict]:
        """Analyze specific IP addresses for known services"""
        reasons = []
        risk_score = 0.1
        
        # Major DNS servers
        if ip_address in ["8.8.8.8", "8.8.4.4"]:
            reasons.append("CRITICAL: Google DNS server")
            risk_score = 0.95
        elif ip_address in ["1.1.1.1", "1.0.0.1"]:
            reasons.append("CRITICAL: Cloudflare DNS server")
            risk_score = 0.95
        elif ip_address in ["208.67.222.222", "208.67.220.220"]:
            reasons.append("HIGH RISK: OpenDNS server")
            risk_score = 0.8
        
        # Common infrastructure
        elif ip_address.startswith("52."):
            reasons.append("MEDIUM RISK: AWS infrastructure range")
            risk_score = 0.6
        elif ip_address.startswith("104.16."):
            reasons.append("HIGH RISK: Cloudflare infrastructure")
            risk_score = 0.8
        
        # Documentation ranges (safe to block)
        elif ip_address.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
            reasons.append("SAFE: Documentation/test range")
            risk_score = 0.1
        
        return {"reasons": reasons, "risk_score": risk_score} if reasons else None
    
    def _determine_risk_level(self, risk_score: float, reasons: List[str]) -> Tuple[RiskLevel, str]:
        """Determine risk level and suggested action"""
        
        # Check for critical keywords
        critical_keywords = ["CRITICAL", "localhost", "private network", "dns"]
        high_risk_keywords = ["HIGH RISK", "infrastructure", "github"]
        
        has_critical = any(any(keyword.lower() in reason.lower() for keyword in critical_keywords) for reason in reasons)
        has_high_risk = any(any(keyword.lower() in reason.lower() for keyword in high_risk_keywords) for reason in reasons)
        
        if has_critical or risk_score >= 0.9:
            return RiskLevel.CRITICAL, "BLOCK - Critical infrastructure risk"
        elif has_high_risk or risk_score >= 0.7:
            return RiskLevel.HIGH, "MANUAL_REVIEW - High risk, requires approval"
        elif risk_score >= 0.5:
            return RiskLevel.MEDIUM, "WARN - Medium risk, proceed with caution"
        elif risk_score >= 0.3:
            return RiskLevel.LOW, "ALLOW - Low risk, safe to block"
        else:
            return RiskLevel.SAFE, "ALLOW - Safe to block"
    
    async def validate_blocklist_addition(self, ip_address: str, context: Dict = None) -> Dict:
        """Main validation function"""
        analysis = await self.analyze_ip(ip_address, context)
        
        return {
            "ip_address": ip_address,
            "allowed": analysis.suggested_action.startswith("ALLOW"),
            "risk_level": analysis.risk_level.value,
            "confidence": analysis.confidence,
            "action": analysis.suggested_action,
            "reasons": analysis.reasons,
            "recommendation": self._generate_recommendation(analysis),
            "analysis_time": analysis.analysis_time.isoformat(),
            "network_info": analysis.network_info
        }
    
    def _generate_recommendation(self, analysis: IPAnalysis) -> str:
        """Generate human-readable recommendation"""
        if analysis.risk_level == RiskLevel.CRITICAL:
            return f"🚫 CRITICAL: Do not block! This could cause severe infrastructure damage."
        elif analysis.risk_level == RiskLevel.HIGH:
            return f"⚠️ HIGH RISK: Manual review required before blocking."
        elif analysis.risk_level == RiskLevel.MEDIUM:
            return f"🔶 MEDIUM: Proceed with caution. Monitor for impact."
        elif analysis.risk_level == RiskLevel.LOW:
            return f"🔶 LOW RISK: Generally safe to block, monitor for issues."
        else:
            return f"✅ SAFE: No significant risks detected. Safe to block."

async def demonstrate_ip_guardian():
    """Demonstrate IP Guardian functionality"""
    guardian = SimpleIPGuardian()
    
    # Test various IP addresses
    test_cases = [
        # Critical infrastructure
        {"ip": "192.168.1.100", "desc": "Private network"},
        {"ip": "8.8.8.8", "desc": "Google DNS"},
        {"ip": "127.0.0.1", "desc": "Localhost"},
        {"ip": "1.1.1.1", "desc": "Cloudflare DNS"},
        
        # Large networks
        {"ip": "10.0.0.0/8", "desc": "Entire private network"},
        {"ip": "52.0.0.0/12", "desc": "Large AWS range"},
        
        # Safe to block
        {"ip": "192.0.2.42", "desc": "Documentation range"},
        {"ip": "198.51.100.1", "desc": "Test network"},
        {"ip": "203.0.113.5", "desc": "Documentation IP"},
        
        # Single suspicious IPs
        {"ip": "185.220.101.42", "desc": "Random IP"},
        {"ip": "104.244.74.211", "desc": "Suspicious IP"},
    ]
    
    print("🛡️ IP Guardian Agent - Demonstration")
    print("=" * 80)
    print("This AI agent analyzes IP addresses before they're added to the blocklist")
    print("to prevent accidentally blocking critical infrastructure.\n")
    
    for i, test_case in enumerate(test_cases, 1):
        ip = test_case["ip"]
        desc = test_case["desc"]
        
        print(f"{i:2d}. Testing: {ip:<20} ({desc})")
        
        result = await guardian.validate_blocklist_addition(ip)
        
        # Determine status emoji
        if result["action"].startswith("BLOCK"):
            status_emoji = "🚫"
            status_color = "BLOCKED"
        elif result["action"].startswith("MANUAL"):
            status_emoji = "⚠️"
            status_color = "NEEDS APPROVAL"
        elif result["action"].startswith("WARN"):
            status_emoji = "🔶"
            status_color = "CAUTION"
        elif result["action"].startswith("ALLOW"):
            status_emoji = "✅"
            status_color = "APPROVED"
        else:
            status_emoji = "❓"
            status_color = "UNKNOWN"
        
        print(f"    {status_emoji} Status: {status_color}")
        print(f"    🎯 Risk Level: {result['risk_level'].upper()}")
        print(f"    🎲 Confidence: {result['confidence']:.1%}")
        print(f"    💡 Recommendation: {result['recommendation']}")
        
        if result['reasons']:
            print(f"    📋 Key Reasons:")
            for reason in result['reasons'][:2]:  # Show first 2 reasons
                print(f"        • {reason}")
        
        if result.get('network_info') and result['network_info'].get('size', 1) > 1:
            size = result['network_info']['size']
            print(f"    🌐 Network Size: {size:,} addresses")
        
        print()
    
    print("🎯 Summary:")
    print("The IP Guardian successfully identified and prevented blocking of:")
    print("• Critical DNS servers (8.8.8.8, 1.1.1.1)")
    print("• Private networks (192.168.x.x, 10.x.x.x)")
    print("• Localhost (127.0.0.1)")
    print("• Large network ranges that could affect thousands of users")
    print("\nWhile allowing safe blocks of documentation ranges and suspicious IPs.")

async def test_bulk_operation():
    """Test bulk IP validation"""
    guardian = SimpleIPGuardian()
    
    # Simulate a bulk operation with mixed IP types
    bulk_ips = [
        "192.168.1.1",    # Private - should block
        "8.8.8.8",        # DNS - should block
        "203.0.113.42",   # Documentation - should allow
        "198.51.100.1",   # Test range - should allow
        "185.220.101.1",  # Random - should allow
        "127.0.0.1",      # Localhost - should block
        "10.0.0.0/24",    # Private subnet - should block
    ]
    
    print("\n" + "="*80)
    print("🔄 Bulk Operation Test")
    print("="*80)
    print(f"Testing bulk validation of {len(bulk_ips)} IP addresses...\n")
    
    results = {
        "total": len(bulk_ips),
        "approved": 0,
        "blocked": 0,
        "needs_review": 0,
        "caution": 0
    }
    
    dangerous_blocks_prevented = []
    
    for ip in bulk_ips:
        result = await guardian.validate_blocklist_addition(ip)
        
        if result["action"].startswith("BLOCK"):
            results["blocked"] += 1
            dangerous_blocks_prevented.append(ip)
        elif result["action"].startswith("MANUAL"):
            results["needs_review"] += 1
            dangerous_blocks_prevented.append(ip)
        elif result["action"].startswith("WARN"):
            results["caution"] += 1
        elif result["action"].startswith("ALLOW"):
            results["approved"] += 1
    
    print(f"📊 Bulk Operation Results:")
    print(f"   Total IPs processed: {results['total']}")
    print(f"   ✅ Approved for blocking: {results['approved']}")
    print(f"   🔶 Approved with caution: {results['caution']}")
    print(f"   ⚠️  Needs manual review: {results['needs_review']}")
    print(f"   🚫 Blocked (dangerous): {results['blocked']}")
    
    safety_score = (results['approved'] + results['caution'] * 0.5) / results['total']
    print(f"   🎯 Safety Score: {safety_score:.1%}")
    
    if dangerous_blocks_prevented:
        print(f"\n🛡️ Prevented dangerous blocks:")
        for ip in dangerous_blocks_prevented:
            print(f"   • {ip}")
        
        print(f"\n💡 The IP Guardian prevented {len(dangerous_blocks_prevented)} potentially")
        print(f"   dangerous blocks that could have disrupted critical infrastructure!")

if __name__ == "__main__":
    print("🔍 Starting IP Guardian Demonstration...\n")
    asyncio.run(demonstrate_ip_guardian())
    asyncio.run(test_bulk_operation())
    print("\n✨ IP Guardian demonstration completed!")