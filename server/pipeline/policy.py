#!/usr/bin/env python3
"""
Signet Protocol Policy Engine

HEL (Host Egress List) policy enforcement for secure
AI-to-AI communications with allowlist validation.
"""

import re
import socket
from typing import List, Optional, NamedTuple
from urllib.parse import urlparse

from ..settings import Settings


class PolicyResult(NamedTuple):
    """Result of policy evaluation"""
    allowed: bool
    reason: Optional[str] = None
    host: Optional[str] = None


class PolicyEngine:
    """Enforces HEL egress policies"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.allowed_hosts = set(settings.allowed_hosts)
    
    async def check_policy(self, url: str, api_key: str) -> PolicyResult:
        """Check if URL is allowed by policy"""
        try:
            # Parse URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return PolicyResult(
                    allowed=False,
                    reason="Invalid URL format"
                )
            
            host = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in host:
                host = host.split(':')[0]
            
            # Check against allowlist
            if not self._is_host_allowed(host):
                return PolicyResult(
                    allowed=False,
                    reason=f"Host not in allowlist: {host}",
                    host=host
                )
            
            # Additional security checks
            security_check = await self._security_checks(host, parsed)
            if not security_check.allowed:
                return security_check
            
            return PolicyResult(allowed=True, host=host)
            
        except Exception as e:
            return PolicyResult(
                allowed=False,
                reason=f"Policy check error: {str(e)}"
            )
    
    def _is_host_allowed(self, host: str) -> bool:
        """Check if host is in allowlist"""
        # Direct match
        if host in self.allowed_hosts:
            return True
        
        # Wildcard subdomain match
        for allowed_host in self.allowed_hosts:
            if allowed_host.startswith('*.'):
                domain = allowed_host[2:]
                if host.endswith('.' + domain) or host == domain:
                    return True
        
        return False
    
    async def _security_checks(self, host: str, parsed_url) -> PolicyResult:
        """Additional security validation"""
        # Check for private/internal IP addresses
        try:
            ip = socket.gethostbyname(host)
            if self._is_private_ip(ip):
                return PolicyResult(
                    allowed=False,
                    reason=f"Private IP address not allowed: {ip}"
                )
        except socket.gaierror:
            # DNS resolution failed
            return PolicyResult(
                allowed=False,
                reason=f"DNS resolution failed for: {host}"
            )
        
        # Check for suspicious patterns
        if self._has_suspicious_patterns(host):
            return PolicyResult(
                allowed=False,
                reason=f"Suspicious host pattern: {host}"
            )
        
        # Validate scheme
        if parsed_url.scheme not in ['http', 'https']:
            return PolicyResult(
                allowed=False,
                reason=f"Unsupported scheme: {parsed_url.scheme}"
            )
        
        return PolicyResult(allowed=True)
    
    def _is_private_ip(self, ip: str) -> bool:
        """Check if IP is in private ranges"""
        try:
            import ipaddress
            addr = ipaddress.ip_address(ip)
            return addr.is_private or addr.is_loopback or addr.is_link_local
        except ValueError:
            return True  # Err on side of caution
    
    def _has_suspicious_patterns(self, host: str) -> bool:
        """Check for suspicious host patterns"""
        suspicious_patterns = [
            r'\d+\.\d+\.\d+\.\d+',  # Raw IP addresses
            r'localhost',
            r'127\.0\.0\.1',
            r'0\.0\.0\.0',
            r'\[::1\]',  # IPv6 localhost
            r'metadata\.google',  # Cloud metadata
            r'169\.254\.',  # Link-local
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, host, re.IGNORECASE):
                return True
        
        return False
    
    def add_allowed_host(self, host: str) -> None:
        """Add host to allowlist"""
        self.allowed_hosts.add(host.lower())
    
    def remove_allowed_host(self, host: str) -> None:
        """Remove host from allowlist"""
        self.allowed_hosts.discard(host.lower())
    
    def get_allowed_hosts(self) -> List[str]:
        """Get current allowlist"""
        return sorted(list(self.allowed_hosts))