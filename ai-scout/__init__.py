"""
AI Scout Package

IP Guardian and Security Monitoring Tools
"""

__version__ = "1.0.0"
__author__ = "SecureScout Team"

try:
    from .ai_scout.ip_guardian import IPGuardian
    __all__ = ['IPGuardian']
except ImportError:
    # Dependencies not installed
    __all__ = [] 