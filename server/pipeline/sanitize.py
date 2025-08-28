import re
CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

def sanitize_text(s: str) -> str:
    s = CTRL_RE.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s

def sanitize_payload(payload):
    if isinstance(payload, dict):
        return {k: sanitize_payload(v) for k, v in payload.items()}
    elif isinstance(payload, list):
        return [sanitize_payload(v) for v in payload]
    elif isinstance(payload, str):
        return sanitize_text(payload)
    else:
        return payload
