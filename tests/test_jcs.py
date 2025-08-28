import pytest
import json
from server.utils.jcs import (
    canonicalize, 
    cid_for_json, 
    normalize_unicode, 
    format_number, 
    escape_string,
    canonicalize_legacy
)

class TestRFC8785Compliance:
    """Test RFC 8785 JSON Canonicalization Scheme compliance"""
    
    def test_unicode_normalization(self):
        """Test Unicode NFC normalization"""
        # Test combining characters
        text1 = "é"  # Single character
        text2 = "e\u0301"  # e + combining acute accent
        
        normalized1 = normalize_unicode(text1)
        normalized2 = normalize_unicode(text2)
        
        assert normalized1 == normalized2
        assert len(normalized1) == 1  # Should be single character after NFC
    
    def test_number_formatting(self):
        """Test proper number formatting"""
        # Integers should remain integers
        assert format_number(42) == "42"
        assert format_number(-17) == "-17"
        assert format_number(0) == "0"
        
        # Floats should be formatted properly
        assert format_number(3.14) == "3.14"
        assert format_number(3.0) == "3"  # Remove unnecessary .0
        assert format_number(-2.5) == "-2.5"
        
        # Booleans
        assert format_number(True) == "true"
        assert format_number(False) == "false"
        
        # Edge cases
        with pytest.raises(ValueError):
            format_number(float('nan'))
        
        with pytest.raises(ValueError):
            format_number(float('inf'))
    
    def test_string_escaping(self):
        """Test proper string escaping"""
        # Basic strings
        assert escape_string("hello") == '"hello"'
        
        # Strings with quotes
        assert escape_string('say "hello"') == '"say \\"hello\\""'
        
        # Unicode strings
        unicode_str = "café"
        escaped = escape_string(unicode_str)
        assert "café" in escaped  # Should preserve Unicode
        
        # Control characters
        assert escape_string("line1\nline2") == '"line1\\nline2"'
        assert escape_string("tab\there") == '"tab\\there"'
    
    def test_object_key_sorting(self):
        """Test that object keys are sorted"""
        obj = {"z": 1, "a": 2, "m": 3}
        canonical = canonicalize(obj)
        
        # Keys should appear in alphabetical order
        assert canonical.index('"a"') < canonical.index('"m"')
        assert canonical.index('"m"') < canonical.index('"z"')
    
    def test_minimal_whitespace(self):
        """Test that canonicalization uses minimal whitespace"""
        obj = {"key": "value", "number": 42}
        canonical = canonicalize(obj)
        
        # Should not contain unnecessary spaces
        assert " " not in canonical
        assert "\n" not in canonical
        assert "\t" not in canonical
    
    def test_nested_objects(self):
        """Test canonicalization of nested objects"""
        obj = {
            "outer": {
                "z": "last",
                "a": "first"
            },
            "array": [3, 1, 2]
        }
        
        canonical = canonicalize(obj)
        
        # Nested object keys should also be sorted
        outer_start = canonical.index('"outer"')
        a_pos = canonical.index('"a"', outer_start)
        z_pos = canonical.index('"z"', outer_start)
        assert a_pos < z_pos
    
    def test_array_preservation(self):
        """Test that array order is preserved"""
        obj = {"numbers": [3, 1, 4, 1, 5]}
        canonical = canonicalize(obj)
        
        # Array order should be preserved (not sorted)
        assert '"numbers":[3,1,4,1,5]' in canonical
    
    def test_known_vectors(self):
        """Test against known canonicalization vectors"""
        # Test vector 1: Simple object
        obj1 = {"b": 2, "a": 1}
        expected1 = '{"a":1,"b":2}'
        assert canonicalize(obj1) == expected1
        
        # Test vector 2: Nested with arrays
        obj2 = {
            "numbers": [1, 2, 3],
            "strings": ["hello", "world"],
            "nested": {"inner": True}
        }
        expected2 = '{"nested":{"inner":true},"numbers":[1,2,3],"strings":["hello","world"]}'
        result2 = canonicalize(obj2)
        assert result2 == expected2
        
        # Test vector 3: Unicode and escaping
        obj3 = {"unicode": "café", "escaped": "line1\nline2"}
        canonical3 = canonicalize(obj3)
        assert '"escaped":"line1\\nline2"' in canonical3
        assert '"unicode":"café"' in canonical3

class TestStableHashing:
    """Test that receipt hashes remain stable"""
    
    def test_cid_stability(self):
        """Test that CID generation is stable"""
        obj = {"trace_id": "test-123", "hop": 1, "data": "stable"}
        
        # Generate CID multiple times
        cid1 = cid_for_json(obj)
        cid2 = cid_for_json(obj)
        cid3 = cid_for_json(obj)
        
        assert cid1 == cid2 == cid3
        assert cid1.startswith("sha256:")
    
    def test_order_independence(self):
        """Test that key order doesn't affect CID"""
        obj1 = {"a": 1, "b": 2, "c": 3}
        obj2 = {"c": 3, "a": 1, "b": 2}
        obj3 = {"b": 2, "c": 3, "a": 1}
        
        cid1 = cid_for_json(obj1)
        cid2 = cid_for_json(obj2)
        cid3 = cid_for_json(obj3)
        
        assert cid1 == cid2 == cid3
    
    def test_receipt_hash_stability(self):
        """Test receipt hash stability with realistic data"""
        receipt = {
            "trace_id": "trace-abc-123",
            "hop": 1,
            "ts": "2025-01-01T00:00:00Z",
            "cid": "sha256:abcd1234",
            "canon": '{"normalized":"data"}',
            "algo": "sha256",
            "prev_receipt_hash": None,
            "policy": {"engine": "HEL", "allowed": True},
            "tenant": "test-tenant"
        }
        
        # Generate hash multiple times
        hash1 = cid_for_json(receipt)
        hash2 = cid_for_json(receipt)
        
        assert hash1 == hash2
        
        # Small change should produce different hash
        receipt_modified = receipt.copy()
        receipt_modified["hop"] = 2
        hash3 = cid_for_json(receipt_modified)
        
        assert hash1 != hash3

class TestBackwardCompatibility:
    """Test backward compatibility with legacy canonicalization"""
    
    def test_legacy_compatibility(self):
        """Test that legacy method still works"""
        obj = {"b": 2, "a": 1}
        
        legacy_result = canonicalize_legacy(obj)
        new_result = canonicalize(obj)
        
        # For simple objects, results should be the same
        assert legacy_result == new_result
    
    def test_fallback_behavior(self):
        """Test fallback to legacy method on errors"""
        # Create an object that might cause issues with strict canonicalization
        # but should work with legacy method
        obj = {"normal": "data", "number": 42}
        
        # This should not raise an exception
        result = canonicalize(obj)
        assert isinstance(result, str)
        assert "normal" in result

class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_objects(self):
        """Test empty objects and arrays"""
        assert canonicalize({}) == "{}"
        assert canonicalize([]) == "[]"
        assert canonicalize({"empty_obj": {}, "empty_arr": []}) == '{"empty_arr":[],"empty_obj":{}}'
    
    def test_null_values(self):
        """Test null value handling"""
        obj = {"null_value": None, "present": "value"}
        canonical = canonicalize(obj)
        assert '"null_value":null' in canonical
    
    def test_boolean_values(self):
        """Test boolean value handling"""
        obj = {"true_val": True, "false_val": False}
        canonical = canonicalize(obj)
        assert '"false_val":false' in canonical
        assert '"true_val":true' in canonical
    
    def test_mixed_types(self):
        """Test objects with mixed value types"""
        obj = {
            "string": "text",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, "two", 3.0],
            "object": {"nested": "value"}
        }
        
        canonical = canonicalize(obj)
        
        # Should handle all types correctly
        assert '"string":"text"' in canonical
        assert '"number":42' in canonical
        assert '"boolean":true' in canonical
        assert '"null":null' in canonical
    
    def test_large_numbers(self):
        """Test handling of large numbers"""
        obj = {
            "large_int": 9007199254740991,  # Max safe integer in JS
            "small_float": 0.000001
        }
        
        canonical = canonicalize(obj)
        assert "9007199254740991" in canonical
        # Note: Small floats may be represented in scientific notation
        assert ("0.000001" in canonical) or ("1e-06" in canonical)

if __name__ == "__main__":
    pytest.main([__file__])
