import socket, idna, ipaddress
from typing import Tuple

PRIVATE_REASONS = {
    "loopback": "HEL_RESOLVED_LOOPBACK",
    "private": "HEL_RESOLVED_PRIVATE",
    "linklocal": "HEL_RESOLVED_LINKLOCAL"
}

def resolve_public_ips(host: str) -> Tuple[bool, str]:
    try:
        ascii_host = idna.encode(host).decode()
        infos = socket.getaddrinfo(ascii_host, None)
        seen_any = False
        for family, _, _, _, sockaddr in infos:
            ip = sockaddr[0]
            seen_any = True
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_loopback:
                return (False, PRIVATE_REASONS["loopback"])
            if ip_obj.is_private:
                return (False, PRIVATE_REASONS["private"])
            if ip_obj.is_link_local:
                return (False, PRIVATE_REASONS["linklocal"])
        if not seen_any:
            return (False, "HEL_NO_RESOLUTION")
        return (True, "ok")
    except Exception:
        return (False, "HEL_RESOLUTION_FAILED")
