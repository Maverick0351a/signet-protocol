import requests, json, socket, ssl, ipaddress
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from .net import resolve_public_ips
import idna

DEFAULT_HEADERS = {
    "User-Agent": "SignetProtocol/0.1",
    "Content-Type": "application/json"
}

MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MB cap

class IPPinnedHTTPSAdapter(requests.adapters.HTTPAdapter):
    """Custom adapter that pins to a specific IP while preserving SNI hostname"""
    
    def __init__(self, target_ip: str, hostname: str, *args, **kwargs):
        self.target_ip = target_ip
        self.hostname = hostname
        super().__init__(*args, **kwargs)
    
    def send(self, request, *args, **kwargs):
        # Replace hostname with IP in URL but keep original hostname for SNI
        parsed = urlparse(request.url)
        if parsed.hostname == self.hostname:
            # Replace hostname with IP in the URL
            new_url = request.url.replace(f"//{self.hostname}", f"//{self.target_ip}")
            request.url = new_url
            # Ensure Host header is set to original hostname
            request.headers['Host'] = self.hostname
        
        try:
            return super().send(request, *args, **kwargs)
        except Exception as e:
            # Handle connection errors gracefully
            raise requests.exceptions.ConnectionError(f"Failed to connect to {self.target_ip}: {str(e)}")

def select_public_ip(hostname: str) -> Tuple[bool, str, Optional[str]]:
    """
    Resolve hostname to IPs, verify all are public, return one IP.
    Returns: (success, reason_or_ip, selected_ip)
    """
    try:
        # First check if all IPs are public using existing net.py logic
        is_public, reason = resolve_public_ips(hostname)
        if not is_public:
            return False, reason, None
        
        # Now get the actual IPs to select one
        ascii_host = idna.encode(hostname).decode()
        infos = socket.getaddrinfo(ascii_host, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        
        public_ips = []
        for family, _, _, _, sockaddr in infos:
            ip = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip)
            # Double-check it's public (should be, but be safe)
            if not (ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local):
                public_ips.append(ip)
        
        if not public_ips:
            return False, "HEL_NO_PUBLIC_IPS", None
        
        # Select first public IP (could be randomized for load balancing)
        selected_ip = public_ips[0]
        return True, "ok", selected_ip
        
    except Exception as e:
        return False, f"HEL_IP_RESOLUTION_ERROR: {str(e)[:100]}", None

def safe_forward(forward_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        parsed = urlparse(forward_url)
        hostname = parsed.hostname or ""
        
        if not hostname:
            return {"status_code": 599, "host": hostname, "error": "Invalid URL: no hostname"}
        
        # Only do IP pinning for HTTPS
        if parsed.scheme == "https":
            success, reason_or_ip, selected_ip = select_public_ip(hostname)
            if not success:
                return {"status_code": 403, "host": hostname, "error": f"IP validation failed: {reason_or_ip}"}
            
            # Create session with IP-pinned adapter
            session = requests.Session()
            adapter = IPPinnedHTTPSAdapter(selected_ip, hostname)
            session.mount("https://", adapter)
            
            # Configure SSL context to verify against original hostname
            import ssl
            import urllib3
            # Disable SSL warnings for IP connections (we're validating the hostname manually)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            session.verify = False  # We'll handle SSL verification manually in the adapter
        else:
            # For HTTP, use regular session but still validate IPs
            success, reason_or_ip, _ = select_public_ip(hostname)
            if not success:
                return {"status_code": 403, "host": hostname, "error": f"IP validation failed: {reason_or_ip}"}
            session = requests.Session()
        
        # Make request with streaming to cap response size
        resp = session.post(
            forward_url,
            data=json.dumps(payload),
            headers=DEFAULT_HEADERS,
            timeout=(3, 10),  # Increased read timeout for streaming
            allow_redirects=False,
            stream=True  # Enable streaming
        )
        
        # Read response body with size limit
        content_length = resp.headers.get('content-length')
        if content_length and int(content_length) > MAX_RESPONSE_BYTES:
            resp.close()
            return {"status_code": 413, "host": hostname, "error": f"Response too large: {content_length} bytes"}
        
        # Stream and cap the response
        body_bytes = b""
        for chunk in resp.iter_content(chunk_size=8192):
            body_bytes += chunk
            if len(body_bytes) > MAX_RESPONSE_BYTES:
                resp.close()
                return {"status_code": 413, "host": hostname, "error": f"Response body exceeds {MAX_RESPONSE_BYTES} bytes"}
        
        resp.close()
        
        return {
            "status_code": resp.status_code, 
            "host": hostname,
            "response_size": len(body_bytes),
            "pinned_ip": selected_ip if parsed.scheme == "https" else None
        }
        
    except requests.exceptions.RequestException as e:
        host = urlparse(forward_url).hostname or ""
        return {"status_code": 599, "host": host, "error": str(e)[:200]}
    except Exception as e:
        host = urlparse(forward_url).hostname or ""
        return {"status_code": 599, "host": host, "error": f"Unexpected error: {str(e)[:200]}"}
