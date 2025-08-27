#!/usr/bin/env python3
"""
Signet Protocol Cryptographic Utilities

Provides Ed25519 signing, verification, and key management
for cryptographic receipts and audit trails.
"""

import json
import hashlib
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import base64


class SigningManager:
    """Manages cryptographic signing for receipts"""
    
    def __init__(self, private_key_pem: Optional[str] = None):
        """Initialize with private key or generate new one"""
        if private_key_pem and private_key_pem != "demo_private_key_change_in_production":
            # Load existing key
            self.private_key = serialization.load_pem_private_key(
                private_key_pem.encode(),
                password=None
            )
        else:
            # Generate new key for demo/development
            self.private_key = Ed25519PrivateKey.generate()
        
        self.public_key = self.private_key.public_key()
    
    def sign_data(self, data: Dict[str, Any]) -> str:
        """Sign data and return base64 signature"""
        # Canonicalize JSON (RFC 8785 JCS)
        canonical_json = self._canonicalize_json(data)
        
        # Sign the canonical bytes
        signature = self.private_key.sign(canonical_json.encode('utf-8'))
        
        # Return base64 encoded signature
        return base64.b64encode(signature).decode('ascii')
    
    def verify_signature(self, data: Dict[str, Any], signature: str) -> bool:
        """Verify a signature against data"""
        try:
            # Canonicalize JSON
            canonical_json = self._canonicalize_json(data)
            
            # Decode signature
            sig_bytes = base64.b64decode(signature)
            
            # Verify signature
            self.public_key.verify(sig_bytes, canonical_json.encode('utf-8'))
            return True
        except (InvalidSignature, Exception):
            return False
    
    def get_public_key_pem(self) -> str:
        """Get public key in PEM format"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('ascii')
    
    def get_public_key_jwk(self) -> Dict[str, str]:
        """Get public key in JWK format for JWKS endpoint"""
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return {
            "kty": "OKP",
            "crv": "Ed25519",
            "x": base64.urlsafe_b64encode(public_bytes).decode('ascii').rstrip('='),
            "use": "sig",
            "alg": "EdDSA"
        }
    
    def _canonicalize_json(self, data: Dict[str, Any]) -> str:
        """Canonicalize JSON according to RFC 8785 JCS"""
        return json.dumps(data, ensure_ascii=True, separators=(',', ':'), sort_keys=True)


def compute_content_hash(data: Any) -> str:
    """Compute SHA-256 hash of content"""
    if isinstance(data, dict):
        # Canonicalize JSON first
        canonical = json.dumps(data, ensure_ascii=True, separators=(',', ':'), sort_keys=True)
        content = canonical.encode('utf-8')
    elif isinstance(data, str):
        content = data.encode('utf-8')
    else:
        content = str(data).encode('utf-8')
    
    hash_obj = hashlib.sha256(content)
    return f"sha256:{hash_obj.hexdigest()}"


def generate_trace_id() -> str:
    """Generate a unique trace ID"""
    import uuid
    return f"signet-{uuid.uuid4().hex[:12]}"