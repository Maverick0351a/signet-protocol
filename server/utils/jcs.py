#!/usr/bin/env python3
"""
JSON Canonicalization Scheme (JCS) - RFC 8785

Implements RFC 8785 JSON Canonicalization Scheme for
cryptographic operations requiring deterministic JSON.
"""

import json
import math
from typing import Any, Dict, List, Union


def canonicalize(data: Any) -> str:
    """Canonicalize JSON data according to RFC 8785"""
    return json.dumps(
        _transform_value(data),
        ensure_ascii=True,
        separators=(',', ':'),
        sort_keys=True
    )


def _transform_value(value: Any) -> Any:
    """Transform a value for canonicalization"""
    if value is None:
        return None
    elif isinstance(value, bool):
        return value
    elif isinstance(value, int):
        return _transform_number(value)
    elif isinstance(value, float):
        return _transform_number(value)
    elif isinstance(value, str):
        return value
    elif isinstance(value, list):
        return [_transform_value(item) for item in value]
    elif isinstance(value, dict):
        return {key: _transform_value(val) for key, val in value.items()}
    else:
        # Convert other types to string
        return str(value)


def _transform_number(number: Union[int, float]) -> Union[int, float, str]:
    """Transform numbers according to RFC 8785 rules"""
    if isinstance(number, int):
        # Integers are preserved as-is if within safe range
        if -(2**53) + 1 <= number <= (2**53) - 1:
            return number
        else:
            # Large integers become strings
            return str(number)
    
    elif isinstance(number, float):
        # Handle special float values
        if math.isnan(number):
            return "NaN"
        elif math.isinf(number):
            return "Infinity" if number > 0 else "-Infinity"
        elif number == 0.0:
            return 0  # Normalize -0.0 to 0
        else:
            # Use the shortest representation
            return number
    
    return number


def verify_canonicalization(original: str, expected: str) -> bool:
    """Verify that JSON canonicalization produces expected result"""
    try:
        parsed = json.loads(original)
        canonical = canonicalize(parsed)
        return canonical == expected
    except (json.JSONDecodeError, Exception):
        return False


def compute_canonical_hash(data: Any) -> str:
    """Compute SHA-256 hash of canonicalized JSON"""
    import hashlib
    
    canonical = canonicalize(data)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"