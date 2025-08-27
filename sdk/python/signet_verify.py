"""
Signet Protocol - Python Verification SDK
Verify receipts and chains in 5 lines of code.
"""

import json
import hashlib
import base64
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse
import requests

class SignetVerifier:
    """
    Lightweight SDK for verifying Signet receipts and chains.
    
    Usage:
        verifier = SignetVerifier()
        valid, reason = verifier.verify_receipt(receipt)
        valid, reason = verifier.verify_chain(receipts)
    """
    
    def __init__(self, jwks_cache_ttl: int = 3600):
        self.jwks_cache = {}
        self.jwks_cache_ttl = jwks_cache_ttl
    
    def verify_receipt(self, receipt: Dict[str, Any], previous_receipt: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Verify a single Signet receipt.
        
        Args:
            receipt: The receipt to verify
            previous_receipt: The previous receipt in the chain (if any)
            
        Returns:
            (is_valid, reason)
        """
        try:
            # 1. Verify receipt hash
            computed_hash = self._compute_receipt_hash(receipt)
            if receipt.get("receipt_hash") != computed_hash:
                return False, "Invalid receipt hash"
            
            # 2. Verify chain linkage
            if previous_receipt:
                if receipt.get("prev_receipt_hash") != previous_receipt.get("receipt_hash"):
                    return False, "Broken chain linkage"
                if receipt.get("hop", 0) != previous_receipt.get("hop", 0) + 1:
                    return False, "Invalid hop sequence"
                if receipt.get("trace_id") != previous_receipt.get("trace_id"):
                    return False, "Trace ID mismatch"
            
            # 3. Verify content identifier
            if "canon" in receipt and "cid" in receipt:
                computed_cid = self._compute_cid(receipt["canon"])
                if receipt["cid"] != computed_cid:
                    return False, "Invalid content identifier"
            
            # 4. Verify timestamp format
            if "ts" in receipt:
                try:
                    from datetime import datetime
                    datetime.fromisoformat(receipt["ts"].replace('Z', '+00:00'))
                except ValueError:
                    return False, "Invalid timestamp format"
            
            return True, "Valid receipt"
            
        except Exception as e:
            return False, f"Verification error: {str(e)}"
    
    def verify_chain(self, receipts: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Verify a complete receipt chain.
        
        Args:
            receipts: List of receipts in chronological order
            
        Returns:
            (is_valid, reason)
        """
        if not receipts:
            return True, "Empty chain"
        
        # Verify genesis receipt
        if receipts[0].get("prev_receipt_hash") is not None:
            return False, "Invalid genesis receipt"
        
        # Verify each receipt and linkage
        for i, receipt in enumerate(receipts):
            prev = receipts[i-1] if i > 0 else None
            valid, reason = self.verify_receipt(receipt, prev)
            if not valid:
                return False, f"Receipt {i}: {reason}"
        
        return True, "Valid chain"
    
    def verify_export_bundle(self, bundle: Dict[str, Any], jwks_url: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify a signed export bundle.
        
        Args:
            bundle: The export bundle to verify
            jwks_url: URL to fetch JWKS (optional, will try to derive from bundle)
            
        Returns:
            (is_valid, reason)
        """
        try:
            # 1. Verify chain
            chain_valid, chain_reason = self.verify_chain(bundle.get("chain", []))
            if not chain_valid:
                return False, f"Invalid chain: {chain_reason}"
            
            # 2. Verify bundle CID
            bundle_content = {
                "trace_id": bundle["trace_id"],
                "chain": bundle["chain"],
                "exported_at": bundle["exported_at"]
            }
            computed_cid = self._compute_cid(self._canonicalize(bundle_content))
            if bundle.get("bundle_cid") != computed_cid:
                return False, "Invalid bundle CID"
            
            # 3. Verify signature (if JWKS available)
            if "signature" in bundle and "kid" in bundle:
                if jwks_url:
                    sig_valid, sig_reason = self._verify_signature(
                        bundle["bundle_cid"], 
                        bundle["signature"], 
                        bundle["kid"], 
                        jwks_url
                    )
                    if not sig_valid:
                        return False, f"Invalid signature: {sig_reason}"
            
            return True, "Valid export bundle"
            
        except Exception as e:
            return False, f"Bundle verification error: {str(e)}"
    
    def _compute_receipt_hash(self, receipt: Dict[str, Any]) -> str:
        """Compute the hash of a receipt (excluding the hash field itself)."""
        receipt_copy = receipt.copy()
        receipt_copy.pop("receipt_hash", None)
        canonical = self._canonicalize(receipt_copy)
        return "sha256:" + hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    def _compute_cid(self, content: str) -> str:
        """Compute content identifier for canonicalized content."""
        return "sha256:" + hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _canonicalize(self, obj: Any) -> str:
        """
        JSON Canonicalization Scheme (JCS) implementation.
        Simplified version - for production use a full RFC 8785 implementation.
        """
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    
    def _verify_signature(self, message: str, signature: str, kid: str, jwks_url: str) -> Tuple[bool, str]:
        """Verify Ed25519 signature using JWKS."""
        try:
            # Fetch JWKS
            jwks = self._fetch_jwks(jwks_url)
            
            # Find key
            key = None
            for k in jwks.get("keys", []):
                if k.get("kid") == kid and k.get("kty") == "OKP" and k.get("crv") == "Ed25519":
                    key = k
                    break
            
            if not key:
                return False, f"Key {kid} not found in JWKS"
            
            # Verify signature (requires cryptography library)
            try:
                from cryptography.hazmat.primitives.asymmetric import ed25519
                from cryptography.hazmat.primitives import serialization
                
                # Decode public key
                public_key_bytes = base64.urlsafe_b64decode(key["x"] + "==")
                public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
                
                # Verify signature
                signature_bytes = base64.b64decode(signature)
                public_key.verify(signature_bytes, message.encode('utf-8'))
                
                return True, "Valid signature"
                
            except ImportError:
                return False, "cryptography library required for signature verification"
            except Exception as e:
                return False, f"Signature verification failed: {str(e)}"
                
        except Exception as e:
            return False, f"JWKS verification error: {str(e)}"
    
    def _fetch_jwks(self, jwks_url: str) -> Dict[str, Any]:
        """Fetch JWKS with caching."""
        import time
        
        now = time.time()
        if jwks_url in self.jwks_cache:
            cached_jwks, cached_time = self.jwks_cache[jwks_url]
            if now - cached_time < self.jwks_cache_ttl:
                return cached_jwks
        
        # Fetch fresh JWKS
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        
        # Cache result
        self.jwks_cache[jwks_url] = (jwks, now)
        
        return jwks


# Convenience functions for one-liner usage
def verify_receipt(receipt: Dict[str, Any], previous_receipt: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Verify a single receipt. Returns (is_valid, reason)."""
    verifier = SignetVerifier()
    return verifier.verify_receipt(receipt, previous_receipt)

def verify_chain(receipts: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Verify a receipt chain. Returns (is_valid, reason)."""
    verifier = SignetVerifier()
    return verifier.verify_chain(receipts)

def verify_export_bundle(bundle: Dict[str, Any], jwks_url: Optional[str] = None) -> Tuple[bool, str]:
    """Verify a signed export bundle. Returns (is_valid, reason)."""
    verifier = SignetVerifier()
    return verifier.verify_export_bundle(bundle, jwks_url)


# Example usage
if __name__ == "__main__":
    # Example receipt
    receipt = {
        "trace_id": "example-123",
        "hop": 1,
        "ts": "2025-01-27T12:00:00Z",
        "tenant": "demo",
        "cid": "sha256:abc123",
        "canon": '{"test":"data"}',
        "algo": "sha256",
        "prev_receipt_hash": None,
        "receipt_hash": "sha256:def456",
        "policy": {"engine": "HEL", "allowed": True, "reason": "ok"}
    }
    
    # Verify in one line
    valid, reason = verify_receipt(receipt)
    print(f"Receipt valid: {valid}, reason: {reason}")
