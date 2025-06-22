from flask import Blueprint, request, jsonify
import logging
import re
import ipaddress
from datetime import datetime

# Import Gemini NLP explainer
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'ai-scout'))
    from ai_scout.gemini_nlp import GeminiNLPExplainer
except ImportError as e:
    print(f"Warning: Could not import Gemini NLP: {e}")
    GeminiNLPExplainer = None

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__)

# Initialize Gemini explainer
gemini_explainer = None
if GeminiNLPExplainer:
    try:
        gemini_explainer = GeminiNLPExplainer()
        if gemini_explainer.is_available():
            logger.info("✅ Chatbot Gemini integration initialized")
        else:
            logger.warning("⚠️ Gemini API key not available for chatbot")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini for chatbot: {e}")

def extract_ip_addresses(text):
    """Extract IP addresses from text"""
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv4_matches = re.findall(ipv4_pattern, text)
    valid_ips = []
    
    for ip in ipv4_matches:
        try:
            ipaddress.IPv4Address(ip)
            valid_ips.append(ip)
        except ipaddress.AddressValueError:
            continue
    
    return valid_ips

def generate_response(question, detected_ips):
    """Generate response about IP addresses"""
    
    if detected_ips:
        ip = detected_ips[0]
        
        if ip == "8.8.8.8" or ip == "8.8.4.4":
            return f"""🔍 About {ip} (Google DNS):

This is Google's public DNS server - critical internet infrastructure. Blocking would cause:
• DNS resolution failures for millions of users
• Websites becoming unreachable 
• Business applications breaking
• Internet appearing broken

💡 Recommendation: Never block Google DNS servers."""

        elif ip == "1.1.1.1":
            return f"""🔍 About {ip} (Cloudflare DNS):

This is Cloudflare's public DNS server. Blocking would cause:
• DNS resolution failures
• VPN service disruption  
• Website loading issues
• Performance degradation

💡 Recommendation: Avoid blocking Cloudflare DNS."""

        elif ip.startswith("192.168.") or ip.startswith("10."):
            return f"""🔍 About {ip} (Private Network):

This is a private IP address for local network communication. Blocking affects:
• Local file sharing and network drives
• Printer and device connectivity
• Internal applications and services
• Device-to-device communication

💡 Recommendation: Be very careful blocking private IPs."""

        else:
            return f"""🔍 About IP Address {ip}:

General guidance for this IP:
• Check if it's critical infrastructure (DNS, CDN, cloud)
• Verify it's not internal/private addressing
• Consider the scope of blocking impact
• Test in non-production environment first
• Monitor for false positives after blocking

💡 Recommendation: Research the IP owner and purpose before blocking."""

    else:
        return """🔍 IP Blocking Guidance:

When considering blocking an IP address:

1. **Research the IP owner** using WHOIS lookup
2. **Check if it's critical infrastructure** (DNS, CDN, etc.)
3. **Verify it's not internal/private** addressing  
4. **Consider impact scope** (single IP vs. range)
5. **Test in non-production** environment first
6. **Monitor for false positives** after implementation

💡 Ask me about specific IP addresses for detailed analysis!"""

@chatbot_bp.route('/ask', methods=['POST'])
def ask_question():
    """Handle chatbot questions about IP addresses"""
    
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({
                'answer': 'Please ask me a question about IP addresses or network security!',
                'timestamp': datetime.now().isoformat()
            })
        
        # Extract IP addresses from the question
        detected_ips = extract_ip_addresses(question)
        
        # Generate response
        response = generate_response(question, detected_ips)
        
        return jsonify({
            'answer': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chatbot error: {e}")
        return jsonify({
            'answer': 'Sorry, I encountered an error processing your question. Please try again.',
            'timestamp': datetime.now().isoformat()
        }), 500

@chatbot_bp.route('/status', methods=['GET'])
def chatbot_status():
    """Get chatbot status"""
    return jsonify({
        'status': 'online',
        'capabilities': [
            'IP address analysis',
            'Network security guidance', 
            'Blocking decision support'
        ],
        'timestamp': datetime.now().isoformat()
    }) 