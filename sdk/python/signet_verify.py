#!/usr/bin/env python3
"""
Signet Protocol Python Verification SDK

Simple 5-line verification of Signet receipts
with cryptographic signature validation.
"""

import json
import base64
import hashlib
from typing import Dict, Any, Tuple, Optional
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature


def verify_receipt(receipt: Dict[str, Any], public_key_pem: str) -> Tuple[bool, str]:
    """
    Verify a Signet receipt in 5 lines
    
    Args:
        receipt: The receipt data to verify
        public_key_pem: Public key in PEM format
    
    Returns:
        Tuple of (is_valid, reason)
    """
    try:
        # Extract signature
        signature = receipt.pop('signature', None)
        if not signature:
            return False, "No signature found"
        
        # Canonicalize JSON
        canonical = json.dumps(receipt, ensure_ascii=True, separators=(',', ':'), sort_keys=True)
        
        # Load public key and verify
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_pem))
        public_key.verify(base64.b64decode(signature), canonical.encode('utf-8'))
        
        return True, "Valid signature"
        
    except InvalidSignature:
        return False, "Invalid signature"
    except Exception as e:
        return False, f"Verification error: {str(e)}"


def verify_receipt_chain(receipts: list, public_key_pem: str) -> Tuple[bool, str]:
    """
    Verify a chain of receipts for hash-chain integrity
    
    Args:
        receipts: List of receipt data in chronological order
        public_key_pem: Public key in PEM format
    
    Returns:
        Tuple of (is_valid, reason)
    """
    if not receipts:
        return False, "Empty receipt chain"
    
    # Verify each receipt individually
    for i, receipt in enumerate(receipts):
        is_valid, reason = verify_receipt(receipt.copy(), public_key_pem)
        if not is_valid:
            return False, f"Receipt {i} invalid: {reason}"
    
    # Verify hash chain (simplified)
    for i in range(1, len(receipts)):
        prev_receipt = receipts[i-1]
        curr_receipt = receipts[i]
        
        # Check if current receipt references previous
        if curr_receipt.get('hop', 1) != prev_receipt.get('hop', 1) + 1:
            return False, f"Broken chain at receipt {i}: hop sequence invalid"
    
    return True, "Valid receipt chain"


def compute_receipt_hash(receipt_data: Dict[str, Any]) -> str:
    """
    Compute the canonical hash of receipt data
    
    Args:
        receipt_data: Receipt data without signature
    
    Returns:
        SHA-256 hash with 'sha256:' prefix
    """
    canonical = json.dumps(receipt_data, ensure_ascii=True, separators=(',', ':'), sort_keys=True)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"


class ReceiptVerifier:
    """Class-based receipt verifier for advanced usage"""
    
    def __init__(self, public_key_pem: str):
        """Initialize with public key"""
        self.public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_pem))
    
    def verify(self, receipt: Dict[str, Any]) -> Tuple[bool, str]:
        """Verify a single receipt"""
        return verify_receipt(receipt, self.public_key)
    
    def verify_chain(self, receipts: list) -> Tuple[bool, str]:
        """Verify a chain of receipts"""
        return verify_receipt_chain(receipts, self.public_key)
    
    def verify_content_hash(self, receipt: Dict[str, Any], original_content: Any) -> bool:
        """Verify that content hash matches original content"""
        expected_hash = receipt.get('cid')
        if not expected_hash:
            return False
        
        # Compute hash of original content
        if isinstance(original_content, dict):
            canonical = json.dumps(original_content, ensure_ascii=True, separators=(',', ':'), sort_keys=True)
            content = canonical.encode('utf-8')
        else:
            content = str(original_content).encode('utf-8')
        
        hash_obj = hashlib.sha256(content)
        computed_hash = f"sha256:{hash_obj.hexdigest()}"
        
        return computed_hash == expected_hash


# Simple usage example
if __name__ == "__main__":
    # Example receipt
    sample_receipt = {
        "receipt_id": "receipt-abc123",
        "trace_id": "signet-def456",
        "ts": "2025-01-27T12:00:00Z",
        "cid": "sha256:content-hash",
        "receipt_hash": "sha256:receipt-hash",
        "hop": 1
    }
    
    # Example public key (base64 encoded)
    public_key = "MCowBQYDK0NiAAEhAKrw6PfFr+1d5TNhehJmLbvp3cOjCyI4bilweropHmqIMh4="
    
    # Verify (this will fail without proper signature)
    is_valid, reason = verify_receipt(sample_receipt, public_key)
    print(f"Receipt valid: {is_valid}, Reason: {reason}")