import json, re
from typing import Optional, Any
TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

def try_parse_json(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None

def repair_json_string(s: str) -> Optional[Any]:
    obj = try_parse_json(s)
    if obj is not None:
        return obj
    s2 = TRAILING_COMMA_RE.sub(r"\1", s)
    obj = try_parse_json(s2)
    if obj is not None:
        return obj
    if "'" in s:
        s3 = s2.replace("'", '"')
        obj = try_parse_json(s3)
        if obj is not None:
            return obj
    s4 = s.encode("utf-8", "ignore").decode("unicode_escape")
    obj = try_parse_json(s4)
    if obj is not None:
        return obj
    return None
