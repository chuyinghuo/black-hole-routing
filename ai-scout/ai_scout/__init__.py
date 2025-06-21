"""
AI Scout Core Module

Security monitoring and IP Guardian functionality
"""

try:
    from .ip_guardian import IPGuardian
    __all__ = ['IPGuardian']
except ImportError:
    # Dependencies not available
    __all__ = [] 