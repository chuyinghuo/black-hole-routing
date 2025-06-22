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
                network_info={"size": ip_obj.num_addresses, "network": str(ip_obj), "network_analysis": size_risk.get("network_analysis") if size_risk else None}
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
        try:
            # Check for specific critical IPs first
            ip_str = str(ip_obj)
            
            # Google DNS servers
            if ip_str in ["8.8.8.8", "8.8.4.4"]:
                reasons.append("Critical: Google DNS server detected")
                reasons.append("Critical infrastructure: This is a public DNS server used by millions")
                return reasons
            
            # Cloudflare DNS servers
            if ip_str in ["1.1.1.1", "1.0.0.1"]:
                reasons.append("Critical: Cloudflare DNS server detected")
                reasons.append("Critical infrastructure: This is a public DNS server used globally")
                return reasons
            
            # Localhost/loopback
            if ip_str in ["127.0.0.1", "::1"] or ip_str.startswith("127."):
                reasons.append("Critical: Localhost/loopback address detected")
                reasons.append("Critical: Would break local system communication")
                return reasons
            
            # Check for private network ranges
            if ip_obj.is_private:
                reasons.append("Critical: Private network address detected")
                reasons.append("Critical: Would affect internal network communication")
                return reasons
            
            # Check against configured critical networks
            for critical_network in self.critical_networks:
                try:
                    critical_net = ipaddress.ip_network(critical_network)
                    if ip_obj.overlaps(critical_net):
                        reasons.append(f"Critical: Overlaps with essential network {critical_network}")
                        
                        # Add specific explanations for well-known networks
                        if str(critical_net).startswith("127."):
                            reasons.append("Critical: Localhost/loopback network - would break local services")
                        elif str(critical_net).startswith("10.") or str(critical_net).startswith("192.168.") or str(critical_net).startswith("172."):
                            reasons.append("Critical: Private network - would break internal communication")
                        elif "8.8.8" in str(critical_net):
                            reasons.append("Critical: Google DNS infrastructure")
                        elif "1.1.1" in str(critical_net):
                            reasons.append("Critical: Cloudflare DNS infrastructure")
                        
                except ipaddress.AddressValueError:
                    continue
                    
        except Exception as e:
            logger.error(f"Critical network check failed: {str(e)}")
            
        return reasons
    
    def _analyze_network_size(self, ip_obj) -> Optional[Dict]:
        """Analyze the size and scope of the network being blocked"""
        try:
            reasons = []
            risk_score = 0.1
            
            if hasattr(ip_obj, 'num_addresses'):
                # It's a network/subnet
                num_addresses = ip_obj.num_addresses
                network_size = ip_obj.prefixlen if hasattr(ip_obj, 'prefixlen') else None
                
                # Calculate percentage of total IPv4/IPv6 space
                if ip_obj.version == 4:
                    total_ipv4_addresses = 2**32  # ~4.3 billion
                    percentage = (num_addresses / total_ipv4_addresses) * 100
                    address_space = "IPv4"
                else:  # IPv6
                    total_ipv6_addresses = 2**128  # Massive number
                    percentage = (num_addresses / total_ipv6_addresses) * 100
                    address_space = "IPv6"
                
                # Detailed impact analysis
                impact_analysis = self._calculate_blocking_impact(num_addresses, percentage, address_space, network_size or 32)
                
                # Categorize based on network size
                if num_addresses >= 16777216:  # /8 or larger - extremely dangerous
                    reasons.append(f"Critical subnet: Contains {num_addresses:,} IP addresses")
                    reasons.append(f"Massive scope: {impact_analysis['scope_description']}")
                    risk_score = 0.95
                elif num_addresses >= 1048576:  # /12 network
                    reasons.append(f"High risk subnet: Contains {num_addresses:,} IP addresses")
                    reasons.append(f"Major scope: {impact_analysis['scope_description']}")
                    risk_score = 0.8
                elif num_addresses >= 65536:  # /16 network
                    reasons.append(f"Medium risk subnet: Contains {num_addresses:,} IP addresses")
                    reasons.append(f"Significant scope: {impact_analysis['scope_description']}")
                    risk_score = 0.7
                elif num_addresses > 4096:  # More than 4096 IPs
                    reasons.append(f"Moderate scope: {impact_analysis['scope_description']}")
                    risk_score = 0.6
                elif num_addresses > 256:  # More than 256 IPs
                    reasons.append(f"📦 Subnet blocking {num_addresses:,} IP addresses")
                    reasons.append(f"Subnet block: Contains {num_addresses:,} IP addresses")
                    reasons.append(f"Small scope: {impact_analysis['scope_description']}")
                    risk_score = 0.5
                elif num_addresses > 1:  # Small subnet
                    reasons.append(f"📦 Subnet blocking {num_addresses:,} IP addresses")
                    reasons.append(f"Small subnet: Contains {num_addresses:,} IP addresses")
                    reasons.append(f"Minimal scope: {impact_analysis['scope_description']}")
                    risk_score = 0.2
                else:
                    # Single IP - no need to show current blocklist count
                    reasons.append(f"Single IP address")
                    risk_score = 0.1
                
                return {
                    "reasons": reasons,
                    "risk_score": risk_score,
                    "network_analysis": {
                        "num_addresses": num_addresses,
                        "percentage_of_internet": percentage,
                        "address_space": address_space,
                        "network_size": network_size,
                        "impact_analysis": impact_analysis
                    }
                }
            else:
                # Single IP address
                if ip_obj.version == 4:
                    percentage = (1 / (2**32)) * 100
                    address_space = "IPv4"
                else:
                    percentage = (1 / (2**128)) * 100
                    address_space = "IPv6"
                
                impact_analysis = self._calculate_blocking_impact(1, percentage, address_space, 32 if ip_obj.version == 4 else 128)
                
                # Get current blocked IP count from database for context
                try:
                    from models import Blocklist
                    current_blocked_count = Blocklist.query.count()
                    reasons.append(f"Single IP address")
                except Exception:
                    reasons.append(f"Single {address_space} address")
                
                reasons.append(f"Minimal scope: {impact_analysis['scope_description']}")
                
                return {
                    "reasons": reasons,
                    "risk_score": 0.1,
                    "network_analysis": {
                        "num_addresses": 1,
                        "percentage_of_internet": percentage,
                        "address_space": address_space,
                        "network_size": 32 if ip_obj.version == 4 else 128,
                        "impact_analysis": impact_analysis
                    }
                }
                
        except Exception as e:
            logger.error(f"Network size analysis failed: {str(e)}")
            return None

    def _calculate_blocking_impact(self, num_addresses: int, percentage: float, address_space: str, network_size: int) -> Dict:
        """Calculate the real-world impact of blocking this many IP addresses"""
        
        # Estimate potential users affected (rough calculation)
        # Assume average of 2-4 users per IP for residential, 10-100 for business networks
        estimated_users_min = num_addresses * 2
        estimated_users_max = num_addresses * 50
        
        # Categorize the scope
        if num_addresses >= 16777216:  # /8 network or larger
            scope_level = "CATASTROPHIC"
            scope_description = f"Entire /8 network ({num_addresses:,} IPs) - would affect major ISPs or entire countries"
            user_impact = f"Could affect {estimated_users_min//1000000}-{estimated_users_max//1000000} million users"
        elif num_addresses >= 1048576:  # /12 network
            scope_level = "MASSIVE"
            scope_description = f"Large ISP network block ({num_addresses:,} IPs) - would affect major service providers"
            user_impact = f"Could affect {estimated_users_min//1000000}-{estimated_users_max//1000000} million users"
        elif num_addresses >= 65536:  # /16 network
            scope_level = "MAJOR"
            scope_description = f"Regional ISP or large organization network ({num_addresses:,} IPs)"
            user_impact = f"Could affect {estimated_users_min//1000}-{estimated_users_max//1000} thousand users"
        elif num_addresses >= 4096:  # /20 network
            scope_level = "SIGNIFICANT"
            scope_description = f"Medium business or local ISP network ({num_addresses:,} IPs)"
            user_impact = f"Could affect {estimated_users_min//1000}-{estimated_users_max//1000} thousand users"
        elif num_addresses >= 256:  # /24 network
            scope_level = "MODERATE"
            scope_description = f"Small business or subnet network ({num_addresses:,} IPs)"
            user_impact = f"Could affect {estimated_users_min}-{estimated_users_max} users"
        elif num_addresses >= 16:  # /28 network
            scope_level = "SMALL"
            scope_description = f"Small subnet or device group ({num_addresses:,} IPs)"
            user_impact = f"Could affect {estimated_users_min}-{estimated_users_max} users"
        elif num_addresses > 1:
            scope_level = "MINIMAL"
            scope_description = f"Small range of {num_addresses:,} IP addresses"
            user_impact = f"Could affect {estimated_users_min}-{estimated_users_max} users"
        else:
            scope_level = "SINGLE"
            scope_description = "Single IP address - minimal impact"
            user_impact = "Could affect 1-10 users"
        
        # Calculate economic impact estimates
        if num_addresses >= 1000000:
            economic_impact = "Potentially millions in lost revenue and service disruption"
        elif num_addresses >= 100000:
            economic_impact = "Potentially hundreds of thousands in lost revenue"
        elif num_addresses >= 10000:
            economic_impact = "Potentially tens of thousands in lost revenue"
        elif num_addresses >= 1000:
            economic_impact = "Potentially thousands in lost revenue"
        else:
            economic_impact = "Minimal economic impact expected"
        
        # Calculate recovery time estimates
        if num_addresses >= 1000000:
            recovery_time = "Days to weeks to identify and resolve issues"
        elif num_addresses >= 100000:
            recovery_time = "Hours to days to resolve service issues"
        elif num_addresses >= 10000:
            recovery_time = "Hours to resolve most issues"
        elif num_addresses >= 1000:
            recovery_time = "Minutes to hours to resolve issues"
        else:
            recovery_time = "Minutes to resolve any issues"
        
        return {
            "scope_level": scope_level,
            "scope_description": scope_description,
            "user_impact": user_impact,
            "economic_impact": economic_impact,
            "recovery_time": recovery_time,
            "network_classification": self._classify_network_size(network_size, address_space),
            "internet_percentage_readable": self._format_percentage(percentage),
            "addresses_formatted": f"{num_addresses:,}"
        }
    
    def _classify_network_size(self, network_size: int, address_space: str) -> str:
        """Classify the network size in human-readable terms"""
        if address_space == "IPv4":
            if network_size <= 8:
                return "Massive network block (/8 or larger)"
            elif network_size <= 12:
                return "Very large network block (/12)"
            elif network_size <= 16:
                return "Large network block (/16)"
            elif network_size <= 20:
                return "Medium network block (/20)"
            elif network_size <= 24:
                return "Small network block (/24)"
            elif network_size <= 28:
                return "Very small subnet (/28)"
            elif network_size <= 30:
                return "Tiny subnet (/30)"
            else:
                return "Single IP address (/32)"
        else:  # IPv6
            if network_size <= 32:
                return "Massive IPv6 network block"
            elif network_size <= 48:
                return "Large IPv6 network block"
            elif network_size <= 64:
                return "Medium IPv6 network block"
            elif network_size <= 96:
                return "Small IPv6 network block"
            elif network_size <= 120:
                return "Tiny IPv6 subnet"
            else:
                return "Single IPv6 address"
    
    def _format_percentage(self, percentage: float) -> str:
        """Format percentage in human-readable form"""
        if percentage >= 1.0:
            return f"{percentage:.2f}% of the internet"
        elif percentage >= 0.01:
            return f"{percentage:.4f}% of the internet"
        elif percentage >= 0.0001:
            return f"{percentage:.6f}% of the internet"
        else:
            return "Single IP address (minimal internet impact)"
    
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
                    reasons.append(f"High risk: Major cloud/service provider ({org})")
                    risk_score = 0.8
                
                # Check for ISPs
                if any(term in org for term in ["isp", "telecom", "internet service", "broadband"]):
                    reasons.append(f"Medium risk: ISP network ({org})")
                    risk_score = 0.6
                
                # Check for universities or government
                if any(term in org for term in ["university", "edu", "government", "gov"]):
                    reasons.append(f"High risk: Educational/Government network ({org})")
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
        
        # Only flag truly critical infrastructure - be very conservative
        critical_keywords = ["Google DNS", "Cloudflare DNS", "localhost", "127.0.0.1", "::1", "private network", "10.0.0", "192.168.", "172.16."]
        high_risk_keywords = ["government", "university", "major cloud provider", "AWS", "Microsoft", "Azure"]
        
        # Check if ANY reason contains critical keywords
        has_critical = any(any(keyword.lower() in reason.lower() for keyword in critical_keywords) for reason in reasons)
        has_high_risk = any(any(keyword.lower() in reason.lower() for keyword in high_risk_keywords) for reason in reasons)
        
        # Risk level determination - be much more conservative
        if has_critical:
            return RiskLevel.CRITICAL, "Block - Critical infrastructure risk detected"
        elif has_high_risk or risk_score >= 0.9:  # Only very high scores get high risk
            return RiskLevel.HIGH, "Manual review - High risk, requires approval"
        elif risk_score >= 0.7:  # Raised threshold for medium risk
            return RiskLevel.MEDIUM, "Warn - Medium risk, proceed with caution"
        elif risk_score >= 0.3:  # Most regular IPs will be low risk
            return RiskLevel.LOW, "Allow - Low risk, safe to block"
        else:
            return RiskLevel.SAFE, "Safe - No significant risks detected"
    
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
        
        # Try to get enhanced explanation from Gemini if available
        if self.gemini_explainer and self.gemini_explainer.is_available():
            try:
                # Use synchronous call to avoid event loop conflicts
                gemini_result = self.gemini_explainer.generate_advanced_explanation(
                    analysis.ip_address,
                    analysis.risk_level.value,
                    analysis.reasons,
                    analysis.confidence
                )
                
                # Format Gemini response
                gemini_explanation = self._format_gemini_explanation(gemini_result, analysis.risk_level)
                if gemini_explanation:
                    return gemini_explanation
            except Exception as e:
                logger.warning(f"Gemini explanation failed, falling back to standard: {e}")
        
        # Fallback to enhanced local explanation system
        explanation = self._generate_detailed_explanation(analysis)
        
        if analysis.risk_level == RiskLevel.CRITICAL:
            return f"🚫 Critical risk - Do not block!\n\n{explanation}\n\nAlternative: Consider allowlisting this IP instead or investigating the source of malicious activity."
        elif analysis.risk_level == RiskLevel.HIGH:
            return f"⚠️ High risk - Manual review required\n\n{explanation}\n\nRecommended action: Have a network administrator review this decision before proceeding."
        elif analysis.risk_level == RiskLevel.MEDIUM:
            return f"🔶 Medium risk - Proceed with caution\n\n{explanation}\n\nRecommended action: Monitor network traffic after blocking for any service disruptions."
        elif analysis.risk_level == RiskLevel.LOW:
            return f"🟡 Low risk - Generally safe\n\n{explanation}\n\nRecommended action: Safe to proceed, but maintain monitoring for false positives."
        else:
            return f"✅ Safe to block\n\n{explanation}\n\nRecommended action: No significant risks detected. Proceed with blocking."
    
    def _generate_detailed_explanation(self, analysis: IPAnalysis) -> str:
        """Generate detailed AI-powered explanation of blocking consequences"""
        
        explanations = []
        
        # Analyze each reason and provide detailed context
        for reason in analysis.reasons:
            if "Google DNS" in reason:
                explanations.append(
                    "Critical infrastructure: Blocking Google DNS would break internet connectivity for millions of users and cause cascading network failures."
                )
            
            elif "Cloudflare DNS" in reason:
                explanations.append(
                    "DNS infrastructure: Blocking Cloudflare DNS would cause resolution failures and break VPN services for many users."
                )
            
            elif "private network" in reason.lower():
                explanations.append(
                    "Private network: This IP is used for internal communication. Blocking could break file sharing, printers, and internal services."
                )
            
            elif "localhost" in reason.lower():
                explanations.append(
                    "Localhost: Essential for local system communication. Blocking would break local applications and development tools."
                )
            
            elif "cloud provider" in reason.lower() or "AWS" in reason or "Microsoft" in reason or "Azure" in reason:
                explanations.append(
                    "Cloud infrastructure: Blocking could affect business applications, email services, and remote work capabilities."
                )
            
            elif "CDN" in reason or "content delivery" in reason.lower():
                explanations.append(
                    "Content delivery: Blocking could slow down website loading and affect media streaming."
                )
            
            elif "government" in reason.lower():
                explanations.append(
                    "Government network: Blocking could interfere with official communications and have legal implications."
                )
            
            elif "university" in reason.lower() or "education" in reason.lower():
                explanations.append(
                    "Educational network: Blocking could affect research collaboration and student access to resources."
                )
            
            elif "ISP" in reason or "internet service provider" in reason.lower():
                explanations.append(
                    "ISP infrastructure: Blocking could affect thousands of legitimate users on this provider."
                )
            
            elif "large network" in reason.lower() or "affects many IPs" in reason:
                explanations.append(
                    "Large network: This block would affect many IP addresses with high probability of blocking legitimate users."
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
            impact_factors.append("High confidence in risk assessment")
        elif analysis.confidence > 0.7:
            impact_factors.append("Moderate confidence with some risk indicators")
        else:
            impact_factors.append("Lower confidence due to limited data")
        
        # Analyze number of reasons
        if len(analysis.reasons) > 5:
            impact_factors.append("Multiple risk factors identified")
        elif len(analysis.reasons) > 2:
            impact_factors.append("Several risk factors present")
        else:
            impact_factors.append("Limited risk factors detected")
        
        # General network impact
        if analysis.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            impact_factors.append("Potential for significant network disruption")
        
        return "General analysis: " + ". ".join(impact_factors) + "."
    
    def _assess_business_impact(self, analysis: IPAnalysis) -> str:
        """Assess potential business impact of blocking this IP"""
        
        if analysis.risk_level == RiskLevel.CRITICAL:
            return "Business impact: Could cause major service outages affecting revenue and customer trust. Recovery time: hours to days."
        elif analysis.risk_level == RiskLevel.HIGH:
            return "Business impact: May cause service degradation requiring manual intervention. Recovery time: minutes to hours."
        elif analysis.risk_level == RiskLevel.MEDIUM:
            return "Business impact: Minor impact expected with limited effect on operations."
        
        return None
    
    def _suggest_alternatives(self, analysis: IPAnalysis) -> str:
        """Suggest alternative security measures instead of blocking"""
        
        alternatives = []
        
        if analysis.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            alternatives.append("Consider rate limiting, geo-blocking, or allowlist approach instead of complete blocking")
        
        if "DNS" in " ".join(analysis.reasons):
            alternatives.append("Try DNS filtering or custom DNS configuration instead")
        
        if "cloud" in " ".join(analysis.reasons).lower():
            alternatives.append("Use application-level blocking or cloud security groups")
        
        if alternatives:
            return "Alternatives: " + ". ".join(alternatives) + "."
        
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
            RiskLevel.CRITICAL: "Critical risk - Do not block!",
            RiskLevel.HIGH: "High risk - Manual review required",
            RiskLevel.MEDIUM: "Medium risk - Proceed with caution",
            RiskLevel.LOW: "Low risk - Generally safe",
            RiskLevel.SAFE: "Safe to block"
        }.get(risk_level, "Unknown risk")
        
        # Build formatted explanation
        sections = []
        
        # Main explanation
        if gemini_result.get("explanation"):
            sections.append(f"AI analysis:\n{gemini_result['explanation']}")
        
        # Technical impact
        if gemini_result.get("technical_impact"):
            sections.append(f"Technical impact:\n{gemini_result['technical_impact']}")
        
        # Business impact
        if gemini_result.get("business_impact"):
            sections.append(f"Business impact:\n{gemini_result['business_impact']}")
        
        # Alternatives
        if gemini_result.get("alternatives"):
            sections.append(f"Alternative measures:\n{gemini_result['alternatives']}")
        
        # Recommendations
        if gemini_result.get("recommendations"):
            sections.append(f"Recommendations:\n{gemini_result['recommendations']}")
        
        # Severity justification
        if gemini_result.get("severity_justification"):
            sections.append(f"Risk assessment:\n{gemini_result['severity_justification']}")
        
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