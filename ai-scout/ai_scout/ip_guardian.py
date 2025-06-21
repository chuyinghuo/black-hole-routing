"""
AI-Powered IP Guardian Agent
Monitors and validates IP addresses before blocklist addition to prevent critical infrastructure blocks
"""

import ipaddress
import re
import asyncio
import aiohttp
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import redis
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Gemini NLP explainer
try:
    from .gemini_nlp import GeminiNLPExplainer
    GEMINI_AVAILABLE = True
    print("✅ Gemini NLP module loaded successfully")
except ImportError as e:
    GEMINI_AVAILABLE = False
    print(f"⚠️  Gemini NLP not available: {e}")
    GeminiNLPExplainer = None

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
    geolocation: Optional[Dict] = None
    reputation_data: Optional[Dict] = None
    network_info: Optional[Dict] = None

class IPGuardianAgent:
    """AI agent that monitors and validates IP addresses before blocklist addition"""
    
    def __init__(self, redis_host='localhost', redis_port=6379):
        try:
            self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            # Test Redis connection
            self.redis_client.ping()
            self.redis_enabled = True
        except Exception:
            self.redis_client = None
            self.redis_enabled = False
            logger.warning("Redis not available, running without cache")
            
        self.critical_networks = self._load_critical_networks()
        self.trusted_sources = self._load_trusted_sources()
        self.analysis_cache = {}
        self.blocked_count_threshold = 1000  # Alert if blocking would affect >1000 IPs
        
        # Initialize Gemini NLP explainer
        if GEMINI_AVAILABLE:
            try:
                self.gemini_explainer = GeminiNLPExplainer()
                logger.info("✅ Gemini NLP explainer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini NLP: {e}")
                self.gemini_explainer = None
        else:
            self.gemini_explainer = None
        
        # Initialize local database for IP intelligence
        self.db_path = Path("ip_intelligence.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for IP intelligence storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ip_analysis (
                ip_address TEXT PRIMARY KEY,
                risk_level TEXT,
                confidence REAL,
                reasons TEXT,
                suggested_action TEXT,
                analysis_time TIMESTAMP,
                geolocation TEXT,
                reputation_data TEXT,
                network_info TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocked_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                reason TEXT,
                timestamp TIMESTAMP,
                prevented BOOLEAN
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_critical_networks(self) -> Set[str]:
        """Load known critical network ranges that should never be blocked"""
        critical_networks = {
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
            
            # Multicast
            "224.0.0.0/4",
            "ff00::/8",
            
            # Major cloud providers (examples - would be more comprehensive)
            "52.0.0.0/8",      # AWS
            "104.16.0.0/12",   # Cloudflare
            "8.8.8.0/24",      # Google DNS
            "1.1.1.0/24",      # Cloudflare DNS
            
            # Major ISPs and backbone networks
            "4.0.0.0/8",       # Level 3
            "12.0.0.0/8",      # AT&T
            
            # Government networks (examples)
            "198.81.128.0/17", # US Gov
            "140.82.112.0/20", # GitHub
        }
        return critical_networks
    
    def _load_trusted_sources(self) -> Set[str]:
        """Load trusted IP reputation sources"""
        return {
            "cloudflare",
            "google",
            "microsoft",
            "amazon",
            "github",
            "known_cdn",
            "major_isp"
        }
    
    async def analyze_ip(self, ip_address: str, context: Dict = None) -> IPAnalysis:
        """Comprehensive AI-powered IP analysis"""
        try:
            # Check cache first (skip if Redis not available)
            cached = None
            if self.redis_enabled:
                try:
                    cache_key = f"ip_analysis:{ip_address}"
                    cached = self.redis_client.get(cache_key)
                    if cached:
                        data = json.loads(cached)
                        return IPAnalysis(**data)
                except Exception:
                    # Continue without cache if Redis fails
                    pass
            
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
                risk_factors.append(0.95)  # Very high risk for critical networks
            
            # 2. Network Size Analysis
            size_risk = self._analyze_network_size(ip_obj)
            if size_risk:
                reasons.extend(size_risk["reasons"])
                risk_factors.append(size_risk["risk_score"])
            
            # 3. Geolocation Analysis
            geo_analysis = await self._analyze_geolocation(str(ip_obj.network_address))
            if geo_analysis:
                reasons.extend(geo_analysis["reasons"])
                risk_factors.append(geo_analysis["risk_score"])
            
            # 4. Reputation Check
            reputation_analysis = await self._check_reputation(str(ip_obj.network_address))
            if reputation_analysis:
                reasons.extend(reputation_analysis["reasons"])
                risk_factors.append(reputation_analysis["risk_score"])
            
            # 5. Historical Analysis
            historical_risk = self._analyze_historical_data(ip_address)
            if historical_risk:
                reasons.extend(historical_risk["reasons"])
                risk_factors.append(historical_risk["risk_score"])
            
            # 6. Context Analysis (if provided)
            if context:
                context_risk = self._analyze_context(context)
                if context_risk:
                    reasons.extend(context_risk["reasons"])
                    risk_factors.append(context_risk["risk_score"])
            
            # Calculate overall risk
            overall_risk_score = max(risk_factors) if risk_factors else 0.1
            confidence = min(len(risk_factors) * 0.2 + 0.6, 1.0)
            
            # Determine risk level and action
            risk_level, suggested_action = self._determine_risk_level(overall_risk_score, reasons)
            
            analysis = IPAnalysis(
                ip_address=ip_address,
                risk_level=risk_level,
                confidence=confidence,
                reasons=reasons,
                suggested_action=suggested_action,
                analysis_time=datetime.now(),
                geolocation=geo_analysis.get("geo_data") if geo_analysis else None,
                reputation_data=reputation_analysis.get("reputation_data") if reputation_analysis else None,
                network_info={"size": ip_obj.num_addresses, "network": str(ip_obj)}
            )
            
            # Cache the analysis (skip if Redis not available)
            if self.redis_enabled:
                try:
                    self.redis_client.setex(
                        cache_key, 
                        3600,  # 1 hour cache
                        json.dumps(analysis.__dict__, default=str)
                    )
                except Exception:
                    # Continue without cache if Redis fails
                    pass
            
            # Store in database
            self._store_analysis(analysis)
            
            return analysis
            
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
        """Check if IP is in critical network ranges"""
        reasons = []
        
        for critical_network in self.critical_networks:
            try:
                critical_net = ipaddress.ip_network(critical_network)
                if ip_obj.overlaps(critical_net):
                    reasons.append(f"CRITICAL: Overlaps with essential network {critical_network}")
                    
                    # Additional specific checks
                    if str(critical_net).startswith("127."):
                        reasons.append("CRITICAL: Localhost/loopback network - would break local services")
                    elif str(critical_net).startswith(("10.", "172.16.", "192.168.")):
                        reasons.append("CRITICAL: Private network range - would block internal infrastructure")
                    elif "8.8.8" in str(critical_net):
                        reasons.append("CRITICAL: Google DNS servers - would break internet connectivity")
                    elif "1.1.1" in str(critical_net):
                        reasons.append("CRITICAL: Cloudflare DNS - would break internet connectivity")
                        
            except ValueError:
                continue
                
        return reasons
    
    def _analyze_network_size(self, ip_obj) -> Optional[Dict]:
        """Analyze the size of the network being blocked"""
        num_addresses = ip_obj.num_addresses
        
        if num_addresses == 1:
            return None  # Single IP is generally safe
        
        reasons = []
        risk_score = 0.0
        
        if num_addresses > 16777216:  # /8 network
            reasons.append(f"CRITICAL: Blocking entire /8 network ({num_addresses:,} addresses)")
            risk_score = 0.95
        elif num_addresses > 1048576:  # /12 network
            reasons.append(f"HIGH RISK: Large network block /{ip_obj.prefixlen} ({num_addresses:,} addresses)")
            risk_score = 0.85
        elif num_addresses > 65536:  # /16 network
            reasons.append(f"MEDIUM RISK: Medium network block /{ip_obj.prefixlen} ({num_addresses:,} addresses)")
            risk_score = 0.65
        elif num_addresses > 256:  # /24 network
            reasons.append(f"LOW RISK: Small network block /{ip_obj.prefixlen} ({num_addresses:,} addresses)")
            risk_score = 0.35
        
        if num_addresses > self.blocked_count_threshold:
            reasons.append(f"WARNING: Would block {num_addresses:,} IP addresses")
            risk_score = max(risk_score, 0.7)
        
        return {"reasons": reasons, "risk_score": risk_score} if reasons else None
    
    async def _analyze_geolocation(self, ip_address: str) -> Optional[Dict]:
        """Analyze IP geolocation for risk factors"""
        try:
            # Simulate geolocation lookup (in real implementation, use actual GeoIP service)
            geo_data = await self._mock_geolocation_lookup(ip_address)
            
            reasons = []
            risk_score = 0.1
            
            if geo_data:
                country = geo_data.get("country", "")
                org = geo_data.get("org", "").lower()
                
                # Check for major infrastructure
                if any(provider in org for provider in ["google", "amazon", "microsoft", "cloudflare", "github"]):
                    reasons.append(f"HIGH RISK: Major cloud/service provider ({org})")
                    risk_score = 0.8
                
                # Check for ISPs
                if any(term in org for term in ["isp", "telecom", "internet service", "broadband"]):
                    reasons.append(f"MEDIUM RISK: ISP network ({org})")
                    risk_score = 0.6
                
                # Check for universities or government
                if any(term in org for term in ["university", "edu", "government", "gov"]):
                    reasons.append(f"HIGH RISK: Educational/Government network ({org})")
                    risk_score = 0.75
            
            return {
                "reasons": reasons,
                "risk_score": risk_score,
                "geo_data": geo_data
            } if reasons else None
            
        except Exception as e:
            logger.error(f"Geolocation analysis failed for {ip_address}: {str(e)}")
            return None
    
    async def _mock_geolocation_lookup(self, ip_address: str) -> Dict:
        """Mock geolocation lookup (replace with actual service)"""
        # In real implementation, use services like MaxMind, IPinfo, etc.
        mock_data = {
            "ip": ip_address,
            "country": "US",
            "region": "California",
            "city": "San Francisco",
            "org": "Example ISP Inc",
            "timezone": "America/Los_Angeles"
        }
        
        # Simulate some realistic org names based on IP patterns
        if ip_address.startswith("8.8."):
            mock_data["org"] = "Google LLC"
        elif ip_address.startswith("1.1."):
            mock_data["org"] = "Cloudflare Inc"
        elif ip_address.startswith("52."):
            mock_data["org"] = "Amazon.com Inc"
        
        return mock_data
    
    async def _check_reputation(self, ip_address: str) -> Optional[Dict]:
        """Check IP reputation across multiple sources"""
        try:
            # Simulate reputation check (in real implementation, query actual threat intel feeds)
            reputation_data = await self._mock_reputation_lookup(ip_address)
            
            reasons = []
            risk_score = 0.1
            
            if reputation_data:
                threat_score = reputation_data.get("threat_score", 0)
                categories = reputation_data.get("categories", [])
                
                if threat_score > 80:
                    reasons.append(f"Known malicious IP (threat score: {threat_score})")
                    risk_score = 0.2  # Actually good to block known bad IPs
                elif threat_score > 50:
                    reasons.append(f"Suspicious IP activity (threat score: {threat_score})")
                    risk_score = 0.1
                
                if "cdn" in categories or "legitimate" in categories:
                    reasons.append("HIGH RISK: Legitimate service provider")
                    risk_score = 0.8
                
            return {
                "reasons": reasons,
                "risk_score": risk_score,
                "reputation_data": reputation_data
            } if reasons else None
            
        except Exception as e:
            logger.error(f"Reputation check failed for {ip_address}: {str(e)}")
            return None
    
    async def _mock_reputation_lookup(self, ip_address: str) -> Dict:
        """Mock reputation lookup (replace with actual threat intel services)"""
        # Simulate different reputation scores
        if ip_address.startswith(("8.8.", "1.1.")):
            return {
                "threat_score": 0,
                "categories": ["dns", "legitimate", "cdn"],
                "last_seen": datetime.now().isoformat()
            }
        else:
            return {
                "threat_score": 25,
                "categories": ["unknown"],
                "last_seen": datetime.now().isoformat()
            }
    
    def _analyze_historical_data(self, ip_address: str) -> Optional[Dict]:
        """Analyze historical blocking patterns"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if IP was previously analyzed
            cursor.execute(
                "SELECT * FROM ip_analysis WHERE ip_address = ? ORDER BY analysis_time DESC LIMIT 1",
                (ip_address,)
            )
            previous_analysis = cursor.fetchone()
            
            # Check for recent blocking incidents
            cursor.execute(
                "SELECT COUNT(*) FROM blocked_incidents WHERE ip_address LIKE ? AND timestamp > ?",
                (f"{ip_address.split('/')[0]}%", datetime.now() - timedelta(days=30))
            )
            recent_blocks = cursor.fetchone()[0]
            
            conn.close()
            
            reasons = []
            risk_score = 0.1
            
            if previous_analysis:
                prev_risk = previous_analysis[1]  # risk_level column
                if prev_risk in ["high", "critical"]:
                    reasons.append(f"Previously flagged as {prev_risk} risk")
                    risk_score = 0.6
            
            if recent_blocks > 5:
                reasons.append(f"Similar IPs blocked {recent_blocks} times in last 30 days")
                risk_score = max(risk_score, 0.4)
            
            return {
                "reasons": reasons,
                "risk_score": risk_score
            } if reasons else None
            
        except Exception as e:
            logger.error(f"Historical analysis failed for {ip_address}: {str(e)}")
            return None
    
    def _analyze_context(self, context: Dict) -> Optional[Dict]:
        """Analyze the context of the blocking request"""
        reasons = []
        risk_score = 0.1
        
        # Check if this is an automated block
        if context.get("automated", False):
            reasons.append("Automated blocking - requires extra validation")
            risk_score = 0.4
        
        # Check the source of the block request
        source = context.get("source", "")
        if source in ["honeypot", "ids", "automated_scanner"]:
            risk_score = max(risk_score, 0.2)
        
        # Check for bulk operations
        if context.get("bulk_operation", False):
            reasons.append("Part of bulk operation - increased risk of error")
            risk_score = max(risk_score, 0.5)
        
        return {
            "reasons": reasons,
            "risk_score": risk_score
        } if reasons else None
    
    def _determine_risk_level(self, risk_score: float, reasons: List[str]) -> Tuple[RiskLevel, str]:
        """Determine overall risk level and suggested action"""
        
        # Check for critical keywords in reasons - these override all other scoring
        critical_keywords = ["CRITICAL:", "localhost", "private network", "Google DNS", "Cloudflare DNS", "essential network"]
        high_risk_keywords = ["HIGH RISK:", "major", "provider", "government", "university"]
        
        # If ANY reason contains CRITICAL keywords, immediately escalate to CRITICAL
        has_critical = any(any(keyword.lower() in reason.lower() for keyword in critical_keywords) for reason in reasons)
        has_high_risk = any(any(keyword.lower() in reason.lower() for keyword in high_risk_keywords) for reason in reasons)
        
        if has_critical:
            return RiskLevel.CRITICAL, "BLOCK - Critical infrastructure risk detected"
        elif has_high_risk or risk_score >= 0.7:
            return RiskLevel.HIGH, "MANUAL_REVIEW - High risk, requires approval"
        elif risk_score >= 0.5:
            return RiskLevel.MEDIUM, "WARN - Medium risk, proceed with caution"
        elif risk_score >= 0.3:
            return RiskLevel.LOW, "ALLOW - Low risk, safe to block"
        else:
            return RiskLevel.SAFE, "ALLOW - Safe to block"
    
    def _store_analysis(self, analysis: IPAnalysis):
        """Store analysis results in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO ip_analysis 
                (ip_address, risk_level, confidence, reasons, suggested_action, 
                 analysis_time, geolocation, reputation_data, network_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.ip_address,
                analysis.risk_level.value,
                analysis.confidence,
                json.dumps(analysis.reasons),
                analysis.suggested_action,
                analysis.analysis_time,
                json.dumps(analysis.geolocation) if analysis.geolocation else None,
                json.dumps(analysis.reputation_data) if analysis.reputation_data else None,
                json.dumps(analysis.network_info) if analysis.network_info else None
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {str(e)}")
    
    async def validate_blocklist_addition(self, ip_address: str, context: Dict = None) -> Dict:
        """Main validation function for blocklist additions"""
        analysis = await self.analyze_ip(ip_address, context)
        
        validation_result = {
            "ip_address": ip_address,
            "allowed": analysis.suggested_action.startswith("ALLOW"),
            "risk_level": analysis.risk_level.value,
            "confidence": analysis.confidence,
            "action": analysis.suggested_action,
            "reasons": analysis.reasons,
            "recommendation": self._generate_recommendation(analysis),
            "analysis_time": analysis.analysis_time.isoformat()
        }
        
        # Log the validation attempt
        self._log_validation_attempt(validation_result)
        
        return validation_result
    
    def _generate_recommendation(self, analysis: IPAnalysis) -> str:
        """Generate comprehensive AI-powered recommendation with detailed explanations"""
        
        # Try to get Gemini-powered explanation first
        if self.gemini_explainer and self.gemini_explainer.is_available():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                gemini_result = loop.run_until_complete(
                    self.gemini_explainer.generate_advanced_explanation(
                        analysis.ip_address,
                        analysis.risk_level.value,
                        analysis.reasons,
                        analysis.confidence
                    )
                )
                loop.close()
                
                # Format Gemini response
                gemini_explanation = self._format_gemini_explanation(gemini_result, analysis.risk_level)
                if gemini_explanation:
                    return gemini_explanation
            except Exception as e:
                logger.warning(f"Gemini explanation failed, falling back to standard: {e}")
        
        # Fallback to enhanced local explanation system
        explanation = self._generate_detailed_explanation(analysis)
        
        if analysis.risk_level == RiskLevel.CRITICAL:
            return f"🚫 CRITICAL RISK - DO NOT BLOCK!\n\n{explanation}\n\n💡 ALTERNATIVE: Consider allowlisting this IP instead or investigating the source of malicious activity."
        elif analysis.risk_level == RiskLevel.HIGH:
            return f"⚠️ HIGH RISK - MANUAL REVIEW REQUIRED\n\n{explanation}\n\n🔍 RECOMMENDED ACTION: Have a network administrator review this decision before proceeding."
        elif analysis.risk_level == RiskLevel.MEDIUM:
            return f"🔶 MEDIUM RISK - PROCEED WITH CAUTION\n\n{explanation}\n\n📊 RECOMMENDED ACTION: Monitor network traffic after blocking for any service disruptions."
        elif analysis.risk_level == RiskLevel.LOW:
            return f"🟡 LOW RISK - GENERALLY SAFE\n\n{explanation}\n\n✅ RECOMMENDED ACTION: Safe to proceed, but maintain monitoring for false positives."
        else:
            return f"✅ SAFE TO BLOCK\n\n{explanation}\n\n🎯 RECOMMENDED ACTION: No significant risks detected. Proceed with blocking."
    
    def _generate_detailed_explanation(self, analysis: IPAnalysis) -> str:
        """Generate detailed AI-powered explanation of blocking consequences"""
        
        explanations = []
        
        # Analyze each reason and provide detailed context
        for reason in analysis.reasons:
            if "Google DNS" in reason:
                explanations.append(
                    "🌐 CRITICAL INFRASTRUCTURE IMPACT:\n"
                    "• Blocking Google DNS (8.8.8.8/8.8.4.4) would break internet connectivity for millions of users\n"
                    "• Many applications, routers, and devices are hardcoded to use these servers\n"
                    "• This could cause cascading failures across your entire network infrastructure\n"
                    "• Legal implications: Could be considered service disruption affecting public services"
                )
            
            elif "Cloudflare DNS" in reason:
                explanations.append(
                    "☁️ DNS INFRASTRUCTURE IMPACT:\n"
                    "• Cloudflare DNS (1.1.1.1) is used by millions of devices globally\n"
                    "• Blocking this would cause DNS resolution failures for users who rely on it\n"
                    "• Many privacy-focused applications default to Cloudflare DNS\n"
                    "• Could break VPN services and security applications that depend on it"
                )
            
            elif "private network" in reason.lower():
                explanations.append(
                    "🏠 PRIVATE NETWORK IMPACT:\n"
                    "• This is a private IP address used for internal network communication\n"
                    "• Blocking private IPs could break internal services, file sharing, and device communication\n"
                    "• Could affect printers, IoT devices, internal servers, and workstation connectivity\n"
                    "• May cause authentication issues with domain controllers or internal databases"
                )
            
            elif "localhost" in reason.lower():
                explanations.append(
                    "💻 LOCALHOST IMPACT:\n"
                    "• Localhost (127.0.0.1) is essential for local system communication\n"
                    "• Blocking this would break local applications, databases, and development tools\n"
                    "• Could prevent web servers, APIs, and local services from functioning\n"
                    "• May cause system instability and prevent troubleshooting tools from working"
                )
            
            elif "cloud provider" in reason.lower() or "AWS" in reason or "Microsoft" in reason or "Azure" in reason:
                explanations.append(
                    "☁️ CLOUD INFRASTRUCTURE IMPACT:\n"
                    "• This IP belongs to a major cloud provider (AWS/Azure/GCP)\n"
                    "• Blocking could affect critical business applications hosted in the cloud\n"
                    "• May break email services, web applications, APIs, and data synchronization\n"
                    "• Could impact remote work capabilities and customer-facing services\n"
                    "• Financial impact: Potential service downtime affecting revenue"
                )
            
            elif "CDN" in reason or "content delivery" in reason.lower():
                explanations.append(
                    "🚀 CONTENT DELIVERY IMPACT:\n"
                    "• This IP is part of a Content Delivery Network (CDN)\n"
                    "• Blocking could slow down or break website loading for users\n"
                    "• May affect media streaming, software updates, and file downloads\n"
                    "• Could impact user experience and website performance metrics"
                )
            
            elif "government" in reason.lower():
                explanations.append(
                    "🏛️ GOVERNMENT NETWORK IMPACT:\n"
                    "• This IP belongs to a government network or agency\n"
                    "• Blocking could interfere with legitimate government communications\n"
                    "• May affect compliance with government regulations or contracts\n"
                    "• Could have legal implications if blocking interferes with official business\n"
                    "• Recommended: Contact legal/compliance team before proceeding"
                )
            
            elif "university" in reason.lower() or "education" in reason.lower():
                explanations.append(
                    "🎓 EDUCATIONAL NETWORK IMPACT:\n"
                    "• This IP belongs to an educational institution\n"
                    "• Blocking could affect research collaboration and academic communications\n"
                    "• May interfere with student access to educational resources\n"
                    "• Could impact legitimate academic research and data sharing"
                )
            
            elif "ISP" in reason or "internet service provider" in reason.lower():
                explanations.append(
                    "🌐 ISP INFRASTRUCTURE IMPACT:\n"
                    "• This IP belongs to a major Internet Service Provider\n"
                    "• Blocking could affect thousands of legitimate users on this ISP\n"
                    "• May cause collateral damage to innocent users sharing this IP range\n"
                    "• Could impact business customers and residential users alike"
                )
            
            elif "large network" in reason.lower() or "affects many IPs" in reason:
                explanations.append(
                    "📊 SCALE IMPACT ANALYSIS:\n"
                    "• This block would affect a large number of IP addresses\n"
                    "• High probability of blocking legitimate users along with threats\n"
                    "• Could cause widespread service disruptions\n"
                    "• Recommended: Use more targeted blocking or implement rate limiting instead"
                )
        
        # If no specific explanations were generated, provide general analysis
        if not explanations:
            explanations.append(self._generate_general_impact_analysis(analysis))
        
        # Add business impact assessment
        business_impact = self._assess_business_impact(analysis)
        if business_impact:
            explanations.append(business_impact)
        
        # Add alternative recommendations
        alternatives = self._suggest_alternatives(analysis)
        if alternatives:
            explanations.append(alternatives)
        
        return "\n\n".join(explanations)
    
    def _generate_general_impact_analysis(self, analysis: IPAnalysis) -> str:
        """Generate general impact analysis when specific patterns aren't matched"""
        
        impact_factors = []
        
        # Analyze confidence level
        if analysis.confidence > 0.9:
            impact_factors.append("• High confidence in risk assessment - strong indicators present")
        elif analysis.confidence > 0.7:
            impact_factors.append("• Moderate confidence - some risk indicators detected")
        else:
            impact_factors.append("• Lower confidence - limited data available for assessment")
        
        # Analyze number of reasons
        if len(analysis.reasons) > 5:
            impact_factors.append("• Multiple risk factors identified - comprehensive threat profile")
        elif len(analysis.reasons) > 2:
            impact_factors.append("• Several risk factors present - moderate complexity")
        else:
            impact_factors.append("• Limited risk factors - straightforward case")
        
        # General network impact
        if analysis.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            impact_factors.append("• Potential for significant network or service disruption")
            impact_factors.append("• May affect multiple users or critical infrastructure")
        
        return f"📋 GENERAL IMPACT ANALYSIS:\n" + "\n".join(impact_factors)
    
    def _assess_business_impact(self, analysis: IPAnalysis) -> str:
        """Assess potential business impact of blocking this IP"""
        
        if analysis.risk_level == RiskLevel.CRITICAL:
            return (
                "💼 BUSINESS IMPACT ASSESSMENT:\n"
                "• SEVERE: Could cause major service outages affecting revenue\n"
                "• May result in customer complaints and support tickets\n"
                "• Potential SLA violations and contractual penalties\n"
                "• Could damage company reputation and customer trust\n"
                "• Estimated recovery time: Hours to days depending on infrastructure"
            )
        elif analysis.risk_level == RiskLevel.HIGH:
            return (
                "💼 BUSINESS IMPACT ASSESSMENT:\n"
                "• MODERATE: May cause service degradation or limited outages\n"
                "• Potential impact on specific user groups or services\n"
                "• Could require manual intervention to resolve issues\n"
                "• May affect productivity for certain departments\n"
                "• Estimated recovery time: Minutes to hours"
            )
        elif analysis.risk_level == RiskLevel.MEDIUM:
            return (
                "💼 BUSINESS IMPACT ASSESSMENT:\n"
                "• LOW-MODERATE: Minor impact expected\n"
                "• May cause inconvenience for some users\n"
                "• Generally manageable with standard procedures\n"
                "• Limited effect on overall business operations"
            )
        
        return None
    
    def _suggest_alternatives(self, analysis: IPAnalysis) -> str:
        """Suggest alternative security measures instead of blocking"""
        
        alternatives = []
        
        if analysis.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            alternatives.extend([
                "🔄 ALTERNATIVE SECURITY MEASURES:",
                "• Rate limiting: Limit connections per minute instead of complete blocking",
                "• Geo-blocking: Block specific countries while allowing legitimate traffic",
                "• Deep packet inspection: Analyze traffic content rather than blocking IPs",
                "• Allowlist approach: Explicitly allow known good IPs and block others",
                "• Behavioral analysis: Monitor for suspicious patterns instead of IP-based blocking"
            ])
        
        if "DNS" in " ".join(analysis.reasons):
            alternatives.extend([
                "• DNS filtering: Block malicious domains instead of DNS servers",
                "• Custom DNS configuration: Redirect to internal DNS servers",
                "• DNS monitoring: Log and analyze DNS queries for threats"
            ])
        
        if "cloud" in " ".join(analysis.reasons).lower():
            alternatives.extend([
                "• Application-level blocking: Block specific services instead of entire IP ranges",
                "• API rate limiting: Control access to cloud services",
                "• Cloud security groups: Use provider-native security controls"
            ])
        
        if alternatives:
            return "\n".join(alternatives)
        
        return None
    
    def _log_validation_attempt(self, result: Dict):
        """Log validation attempts for audit trail"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO blocked_incidents 
                (ip_address, reason, timestamp, prevented)
                VALUES (?, ?, ?, ?)
            ''', (
                result["ip_address"],
                result["action"],
                datetime.now(),
                not result["allowed"]
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log validation attempt: {str(e)}")
    
    async def get_validation_stats(self) -> Dict:
        """Get statistics about validation activities"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get recent statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_validations,
                    SUM(CASE WHEN prevented = 1 THEN 1 ELSE 0 END) as prevented_blocks,
                    COUNT(DISTINCT DATE(timestamp)) as active_days
                FROM blocked_incidents 
                WHERE timestamp > ?
            ''', (datetime.now() - timedelta(days=30),))
            
            stats = cursor.fetchone()
            
            # Get risk level distribution
            cursor.execute('''
                SELECT risk_level, COUNT(*) 
                FROM ip_analysis 
                WHERE analysis_time > ?
                GROUP BY risk_level
            ''', (datetime.now() - timedelta(days=30),))
            
            risk_distribution = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                "total_validations": stats[0],
                "prevented_dangerous_blocks": stats[1],
                "active_days": stats[2],
                "risk_distribution": risk_distribution,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation stats: {str(e)}")
            return {}

    def _format_gemini_explanation(self, gemini_result: dict, risk_level: RiskLevel) -> str:
        """Format Gemini AI explanation into the standard recommendation format"""
        
        if not gemini_result or not isinstance(gemini_result, dict):
            return None
        
        # Get risk level emoji
        risk_emoji = {
            RiskLevel.CRITICAL: "🚫",
            RiskLevel.HIGH: "⚠️",
            RiskLevel.MEDIUM: "🔶", 
            RiskLevel.LOW: "🟡",
            RiskLevel.SAFE: "✅"
        }.get(risk_level, "❓")
        
        # Get risk level title
        risk_title = {
            RiskLevel.CRITICAL: "CRITICAL RISK - DO NOT BLOCK!",
            RiskLevel.HIGH: "HIGH RISK - MANUAL REVIEW REQUIRED",
            RiskLevel.MEDIUM: "MEDIUM RISK - PROCEED WITH CAUTION",
            RiskLevel.LOW: "LOW RISK - GENERALLY SAFE",
            RiskLevel.SAFE: "SAFE TO BLOCK"
        }.get(risk_level, "UNKNOWN RISK")
        
        # Build formatted explanation
        sections = []
        
        # Main explanation
        if gemini_result.get("explanation"):
            sections.append(f"🧠 AI ANALYSIS:\n{gemini_result['explanation']}")
        
        # Technical impact
        if gemini_result.get("technical_impact"):
            sections.append(f"⚙️ TECHNICAL IMPACT:\n{gemini_result['technical_impact']}")
        
        # Business impact
        if gemini_result.get("business_impact"):
            sections.append(f"💼 BUSINESS IMPACT:\n{gemini_result['business_impact']}")
        
        # Alternatives
        if gemini_result.get("alternatives"):
            sections.append(f"🔄 ALTERNATIVE MEASURES:\n{gemini_result['alternatives']}")
        
        # Recommendations
        if gemini_result.get("recommendations"):
            sections.append(f"💡 RECOMMENDATIONS:\n{gemini_result['recommendations']}")
        
        # Severity justification
        if gemini_result.get("severity_justification"):
            sections.append(f"📊 RISK ASSESSMENT:\n{gemini_result['severity_justification']}")
        
        # Combine all sections
        explanation_body = "\n\n".join(sections) if sections else "Detailed analysis not available"
        
        return f"{risk_emoji} {risk_title}\n\n{explanation_body}"

# Example usage and testing
async def test_ip_guardian():
    """Test the IP Guardian with various IP addresses"""
    guardian = IPGuardianAgent()
    
    test_ips = [
        "192.168.1.100",      # Private network - should be critical
        "8.8.8.8",           # Google DNS - should be critical
        "127.0.0.1",         # Localhost - should be critical
        "185.199.108.153",    # GitHub - should be high risk
        "1.1.1.1",           # Cloudflare - should be critical
        "198.51.100.42",     # Documentation range - should be safe
        "10.0.0.0/8",        # Entire private network - should be critical
        "192.0.2.1",         # Test range - should be safe
    ]
    
    print("🔍 IP Guardian Agent - Validation Results")
    print("=" * 60)
    
    for ip in test_ips:
        result = await guardian.validate_blocklist_addition(ip)
        status_emoji = "✅" if result["allowed"] else "🚫"
        
        print(f"\n{status_emoji} IP: {ip}")
        print(f"   Risk Level: {result['risk_level'].upper()}")
        print(f"   Action: {result['action']}")
        print(f"   Confidence: {result['confidence']:.2f}")
        print(f"   Recommendation: {result['recommendation']}")
        if result['reasons']:
            print(f"   Key Reasons: {'; '.join(result['reasons'][:2])}")
    
    # Get statistics
    stats = await guardian.get_validation_stats()
    print(f"\n📊 Validation Statistics:")
    print(f"   Total Validations: {stats.get('total_validations', 0)}")
    print(f"   Prevented Dangerous Blocks: {stats.get('prevented_dangerous_blocks', 0)}")
    print(f"   Risk Distribution: {stats.get('risk_distribution', {})}")

if __name__ == "__main__":
    asyncio.run(test_ip_guardian()) 

# Create alias for backward compatibility
IPGuardian = IPGuardianAgent 