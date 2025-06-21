"""
Gemini NLP Integration for IP Guardian
Provides advanced natural language explanations using Google's Gemini AI
"""

import os
import google.generativeai as genai
from typing import Dict, List, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiNLPExplainer:
    """Advanced NLP explainer using Google Gemini AI"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('API_KEY') or os.getenv('GEMINI_API_KEY')
        self.model = None
        self.initialized = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.initialized = True
                logger.info("✅ Gemini NLP initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.initialized = False
        else:
            logger.warning("⚠️ Gemini API key not found. NLP explanations will be limited.")
    
    def is_available(self) -> bool:
        """Check if Gemini is available for use"""
        return self.initialized and self.model is not None
    
    async def generate_advanced_explanation(self, 
                                    ip_address: str, 
                                    risk_level: str,
                                    basic_reasons: List[str],
                                    confidence: float) -> Dict[str, str]:
        """
        Generate advanced NLP explanation using Gemini about why blocking an IP is risky
        """
        
        if not self.is_available():
            return {
                "explanation": "Advanced AI explanation not available - API key required",
                "technical_impact": "Unable to analyze technical impact",
                "business_impact": "Unable to analyze business impact", 
                "alternatives": "Standard security measures recommended"
            }
        
        try:
            # Construct the prompt for Gemini
            prompt = self._build_analysis_prompt(ip_address, risk_level, basic_reasons, confidence)
            
            # Generate response from Gemini
            response = self.model.generate_content(prompt)
            
            # Parse the structured response
            parsed_response = self._parse_gemini_response(response.text)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {
                "explanation": f"AI analysis temporarily unavailable: {str(e)}",
                "technical_impact": "Manual analysis recommended",
                "business_impact": "Consult with network administrators",
                "alternatives": "Consider alternative security measures"
            }
    
    def _build_analysis_prompt(self, 
                              ip_address: str, 
                              risk_level: str, 
                              basic_reasons: List[str], 
                              confidence: float) -> str:
        """Build a comprehensive prompt for Gemini analysis"""
        
        reasons_text = "\n".join([f"- {reason}" for reason in basic_reasons])
        
        prompt = f"""
You are a cybersecurity expert specializing in network infrastructure protection. Analyze why blocking IP address {ip_address} could be dangerous or crucial for network security.

**Current Analysis:**
- IP Address: {ip_address}
- Risk Level: {risk_level}
- Confidence: {confidence:.2%}
- Detection Reasons:
{reasons_text}

**Please provide a comprehensive analysis in JSON format with these exact keys:**

1. "explanation": A detailed, easy-to-understand explanation of why this IP should or shouldn't be blocked
2. "technical_impact": Specific technical consequences of blocking this IP
3. "business_impact": Business and operational impacts (downtime, user experience, revenue)
4. "alternatives": Alternative security measures instead of blocking
5. "severity_justification": Why this risk level is appropriate
6. "recommendations": Specific actionable recommendations

**Guidelines:**
- Use clear, professional language that both technical and non-technical stakeholders can understand
- Be specific about potential impacts and consequences
- Focus on practical implications for network operations
- If this is critical infrastructure (DNS, cloud providers, CDNs), emphasize the catastrophic impact
- If it's a legitimate security threat, explain the proper containment approach
- Provide concrete alternative solutions
- Keep explanations concise but comprehensive

**Output format:** Return ONLY a valid JSON object with the six keys above.
"""
        
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, str]:
        """Parse Gemini's JSON response with fallback handling"""
        
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed = json.loads(json_text)
                
                # Validate required keys
                required_keys = [
                    "explanation", "technical_impact", "business_impact", 
                    "alternatives", "severity_justification", "recommendations"
                ]
                
                result = {}
                for key in required_keys:
                    result[key] = parsed.get(key, f"Analysis for {key} not available")
                
                return result
            else:
                # Fallback if JSON parsing fails
                return self._fallback_parse(response_text)
                
        except json.JSONDecodeError:
            return self._fallback_parse(response_text)
    
    def _fallback_parse(self, response_text: str) -> Dict[str, str]:
        """Fallback parser when JSON parsing fails"""
        
        # Simple text-based parsing as fallback
        lines = response_text.split('\n')
        sections = {}
        current_section = "explanation"
        current_content = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ["technical", "impact"]):
                if current_content:
                    sections[current_section] = ' '.join(current_content)
                current_section = "technical_impact"
                current_content = []
            elif any(keyword in line.lower() for keyword in ["business", "operational"]):
                if current_content:
                    sections[current_section] = ' '.join(current_content)
                current_section = "business_impact" 
                current_content = []
            elif any(keyword in line.lower() for keyword in ["alternative", "instead"]):
                if current_content:
                    sections[current_section] = ' '.join(current_content)
                current_section = "alternatives"
                current_content = []
            elif line:
                current_content.append(line)
        
        # Add the last section
        if current_content:
            sections[current_section] = ' '.join(current_content)
        
        # Ensure all required keys exist
        return {
            "explanation": sections.get("explanation", response_text[:500] + "..."),
            "technical_impact": sections.get("technical_impact", "Detailed technical analysis not available"),
            "business_impact": sections.get("business_impact", "Business impact assessment not available"),
            "alternatives": sections.get("alternatives", "Standard security alternatives recommended"),
            "severity_justification": "AI analysis completed with fallback parsing",
            "recommendations": "Consult with network security team for specific recommendations"
        }
    
    def generate_quick_summary(self, ip_address: str, risk_level: str) -> str:
        """Generate a quick one-sentence summary about the IP"""
        
        if not self.is_available():
            return f"IP {ip_address} has {risk_level} risk level - detailed analysis requires API configuration"
        
        try:
            prompt = f"""
In one clear sentence, explain why IP address {ip_address} with risk level {risk_level} should or shouldn't be blocked. 
Focus on the most critical concern. Be specific and actionable.
"""
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Quick summary generation failed: {e}")
            return f"IP {ip_address} requires careful consideration before blocking due to {risk_level} risk level"

# Example usage and testing
async def test_gemini_nlp():
    """Test the Gemini NLP explainer"""
    
    explainer = GeminiNLPExplainer()
    
    if not explainer.is_available():
        print("❌ Gemini not available - please set API_KEY environment variable")
        return
    
    test_cases = [
        {
            "ip": "8.8.8.8",
            "risk": "CRITICAL", 
            "reasons": ["Google DNS server", "Critical infrastructure", "Millions of users depend on this"],
            "confidence": 0.95
        },
        {
            "ip": "192.168.1.1",
            "risk": "CRITICAL",
            "reasons": ["Private network address", "Internal router", "Would break local network"],
            "confidence": 1.0
        },
        {
            "ip": "198.51.100.42",
            "risk": "SAFE",
            "reasons": ["Documentation IP range", "Not in active use", "Safe to block"],
            "confidence": 0.8
        }
    ]
    
    print("🧠 Testing Gemini NLP Explanations")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\n🔍 Analyzing {test['ip']} ({test['risk']} risk)")
        print("-" * 40)
        
        result = await explainer.generate_advanced_explanation(
            test['ip'], test['risk'], test['reasons'], test['confidence']
        )
        
        print(f"📖 Explanation: {result['explanation'][:200]}...")
        print(f"⚙️  Technical: {result['technical_impact'][:150]}...")
        print(f"💼 Business: {result['business_impact'][:150]}...")
        print(f"🔄 Alternatives: {result['alternatives'][:150]}...")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gemini_nlp()) 