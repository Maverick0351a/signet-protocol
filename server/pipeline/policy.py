from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from .net import resolve_public_ips

class PolicyResult(dict):
    @property
    def allowed(self) -> bool:
        return bool(self.get("allowed", False))

def hel_allow_forward(tenant_allow: List[str], global_allow: List[str], forward_url: Optional[str]) -> PolicyResult:
    if not forward_url:
        return PolicyResult(engine="HEL", allowed=True, reason="no_forward")
    parsed = urlparse(forward_url)
    if parsed.scheme.lower() != "https":
        return PolicyResult(engine="HEL", allowed=False, reason="HEL_SCHEME_NOT_HTTPS")
    host = parsed.hostname
    allow = set([h.lower() for h in (tenant_allow or [])] + [h.lower() for h in (global_allow or [])])
    if host is None or host.lower() not in allow:
        return PolicyResult(engine="HEL", allowed=False, reason="HEL_HOST_NOT_ALLOWED")
    ok, detail = resolve_public_ips(host)
    if not ok:
        return PolicyResult(engine="HEL", allowed=False, reason=detail)
    return PolicyResult(engine="HEL", allowed=True, reason="ok")
