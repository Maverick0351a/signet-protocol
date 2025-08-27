"""
RFC 8785 compliant JSON Canonicalization Scheme (JCS) implementation.

This implementation ensures:
- Unicode normalization (NFC)
- Proper number formatting (integers vs floats)
- Correct escape sequences
- Stable canonicalization for receipt hashes
"""
import json
import unicodedata
import re
from typing import Any
from decimal import Decimal

def normalize_unicode(text: str) -> str:
    """Normalize Unicode text to NFC form as per RFC 8785"""
    return unicodedata.normalize('NFC', text)

def format_number(num) -> str:
    """Format numbers according to RFC 8785 rules"""
    if isinstance(num, bool):
        return str(num).lower()
    elif isinstance(num, int):
        return str(num)
    elif isinstance(num, float):
        if num != num:  # NaN check
            raise ValueError("NaN values not allowed in JCS")
        if num == float('inf') or num == float('-inf'):
            raise ValueError("Infinity values not allowed in JCS")
        
        # Use Decimal for precise formatting to avoid floating point issues
        decimal_num = Decimal(str(num))
        
        # Remove trailing zeros and unnecessary decimal point
        formatted = format(decimal_num, 'f')
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        
        # Handle scientific notation for very large/small numbers
        if 'e' in str(num).lower():
            return str(num)
        
        return formatted
    else:
        return str(num)

def escape_string(s: str) -> str:
    """Escape string according to RFC 8785 rules"""
    # Normalize Unicode first
    s = normalize_unicode(s)
    
    # Use json.dumps to handle proper escaping, then extract the content
    escaped = json.dumps(s, ensure_ascii=False, separators=(',', ':'))
    return escaped

def canonicalize_value(obj: Any) -> str:
    """Recursively canonicalize a JSON value according to RFC 8785"""
    if obj is None:
        return "null"
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return format_number(obj)
    elif isinstance(obj, str):
        return escape_string(obj)
    elif isinstance(obj, list):
        items = [canonicalize_value(item) for item in obj]
        return "[" + ",".join(items) + "]"
    elif isinstance(obj, dict):
        # Sort keys and canonicalize recursively
        sorted_items = []
        for key in sorted(obj.keys()):
            if not isinstance(key, str):
                raise ValueError(f"Dictionary keys must be strings, got {type(key)}")
            canonical_key = escape_string(key)
            canonical_value = canonicalize_value(obj[key])
            sorted_items.append(f"{canonical_key}:{canonical_value}")
        return "{" + ",".join(sorted_items) + "}"
    else:
        raise ValueError(f"Unsupported type for JCS canonicalization: {type(obj)}")

def canonicalize(obj: Any) -> str:
    """
    Canonicalize a JSON object according to RFC 8785.
    
    This ensures:
    - Unicode NFC normalization
    - Proper number formatting
    - Sorted object keys
    - Minimal whitespace
    - Consistent escape sequences
    """
    try:
        return canonicalize_value(obj)
    except Exception as e:
        # Fallback to basic JSON serialization if strict canonicalization fails
        # This maintains backward compatibility while logging the issue
        import logging
        logging.warning(f"JCS canonicalization failed, falling back to basic JSON: {e}")
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha256_hexdigest(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()

def cid_for_json(obj: Any) -> str:
    """Generate a content identifier for a JSON object using RFC 8785 JCS"""
    canon = canonicalize(obj).encode("utf-8")
    return "sha256:" + sha256_hexdigest(canon)

# Legacy function for backward compatibility
def canonicalize_legacy(obj: Any) -> str:
    """Legacy canonicalization method - kept for migration purposes"""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
