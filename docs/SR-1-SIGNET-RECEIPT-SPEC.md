# SR-1: Signet Receipt Specification

**Version:** 1.0  
**Status:** Production Ready  
**Date:** January 2025

## Abstract

This specification defines the Signet Receipt format for cryptographically verifiable audit trails in AI-to-AI communications. Signet Receipts provide immutable proof of data exchanges, transformations, and forwarding operations within the Trust Fabric.

## 1. Introduction

Signet Receipts are cryptographically signed documents that provide:

- **Immutable Audit Trails**: Tamper-evident records of AI interactions
- **Cryptographic Integrity**: Ed25519 signatures ensure authenticity
- **Hash-Chain Linking**: Sequential receipts form verifiable chains
- **Content Verification**: SHA-256 hashes prove data integrity

## 2. Receipt Structure

### 2.1 Core Fields

Every Signet Receipt MUST contain the following fields:

```json
{
  "receipt_id": "receipt-abc123def456",
  "trace_id": "signet-789xyz012",
  "ts": "2025-01-27T12:00:00.000Z",
  "cid": "sha256:content-hash-hex",
  "receipt_hash": "sha256:receipt-hash-hex",
  "hop": 1,
  "signature": "base64-encoded-ed25519-signature"
}
```

### 2.2 Field Definitions

- **receipt_id**: Unique identifier for this receipt (string)
- **trace_id**: Trace identifier linking related operations (string)
- **ts**: ISO 8601 timestamp in UTC (string)
- **cid**: Content Identifier - SHA-256 hash of payload (string)
- **receipt_hash**: SHA-256 hash of canonical receipt data (string)
- **hop**: Sequence number in processing chain (integer)
- **signature**: Ed25519 signature of canonical receipt (string)

### 2.3 Optional Fields

Receipts MAY include additional metadata:

```json
{
  "payload_type": "openai.tooluse.invoice.v1",
  "target_type": "invoice.iso20022.v1",
  "api_key": "tenant-identifier",
  "metadata": {
    "custom_field": "value"
  }
}
```

## 3. Cryptographic Operations

### 3.1 JSON Canonicalization

All JSON data MUST be canonicalized according to RFC 8785 (JCS) before hashing or signing:

1. Remove signature field if present
2. Sort object keys lexicographically
3. Use minimal JSON representation (no whitespace)
4. Ensure ASCII encoding

### 3.2 Content Hash Computation

```python
def compute_content_hash(payload):
    canonical = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"
```

### 3.3 Receipt Hash Computation

```python
def compute_receipt_hash(receipt_data):
    # Remove signature field
    receipt_copy = {k: v for k, v in receipt_data.items() if k != 'signature'}
    canonical = json.dumps(receipt_copy, separators=(',', ':'), sort_keys=True)
    hash_obj = hashlib.sha256(canonical.encode('utf-8'))
    return f"sha256:{hash_obj.hexdigest()}"
```

### 3.4 Digital Signatures

Signet Receipts use Ed25519 digital signatures:

1. Canonicalize receipt data (excluding signature)
2. Sign canonical bytes with Ed25519 private key
3. Encode signature as base64
4. Add signature field to receipt

## 4. Verification Process

### 4.1 Single Receipt Verification

```python
def verify_receipt(receipt, public_key):
    # Extract signature
    signature = receipt.pop('signature')
    
    # Canonicalize remaining data
    canonical = json.dumps(receipt, separators=(',', ':'), sort_keys=True)
    
    # Verify signature
    try:
        public_key.verify(base64.b64decode(signature), canonical.encode('utf-8'))
        return True
    except InvalidSignature:
        return False
```

### 4.2 Chain Verification

For receipt chains, verify:

1. Each individual receipt signature
2. Sequential hop numbering
3. Trace ID consistency
4. Timestamp ordering

## 5. Hash Chain Integrity

### 5.1 Chain Structure

Receipts form hash-linked chains where each receipt references the previous:

```
Receipt 1 (hop=1) → Receipt 2 (hop=2) → Receipt 3 (hop=3)
```

### 5.2 Chain Validation

- Hop numbers MUST increment by 1
- Trace IDs MUST be consistent
- Timestamps MUST be non-decreasing

## 6. Security Considerations

### 6.1 Key Management

- Use secure key generation for Ed25519 keys
- Protect private keys with appropriate access controls
- Implement key rotation procedures
- Distribute public keys via JWKS endpoints

### 6.2 Timestamp Security

- Use UTC timestamps to avoid timezone issues
- Implement clock synchronization
- Consider timestamp tolerance for verification

### 6.3 Hash Collision Resistance

- SHA-256 provides 128-bit security level
- Monitor for cryptographic advances
- Plan for hash algorithm migration

## 7. Implementation Guidelines

### 7.1 Storage Requirements

- Store receipts in tamper-evident storage
- Implement backup and recovery procedures
- Consider long-term archival requirements

### 7.2 Performance Considerations

- Batch verification for large receipt sets
- Cache public keys to reduce lookups
- Use streaming for large audit exports

### 7.3 Error Handling

- Graceful degradation for verification failures
- Detailed error reporting for debugging
- Audit logging for security events

## 8. Examples

### 8.1 Complete Receipt

```json
{
  "receipt_id": "receipt-f47ac10b58cc4372",
  "trace_id": "signet-a1b2c3d4e5f6",
  "ts": "2025-01-27T12:00:00.000Z",
  "payload_type": "openai.tooluse.invoice.v1",
  "target_type": "invoice.iso20022.v1",
  "cid": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "receipt_hash": "sha256:d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35",
  "hop": 1,
  "api_key": "tenant-demo-key",
  "signature": "MEUCIQDxKwwlJrlubAC7DgkEyAOb4CzMkjZKqTXiYzQzYjFmYwIgYzNjZjNjZjNjZjNjZjNjZjNjZjNjZjNjZjNjZjNjZjM="
}
```

### 8.2 Verification Code

```python
from signet_verify import verify_receipt

# Verify receipt
is_valid, reason = verify_receipt(receipt, public_key_pem)
print(f"Receipt valid: {is_valid}, Reason: {reason}")
```

## 9. Compliance

This specification ensures compliance with:

- **RFC 8785**: JSON Canonicalization Scheme
- **RFC 8032**: EdDSA signature algorithms
- **ISO 8601**: Date and time format
- **FIPS 180-4**: SHA-256 hash function

## 10. Version History

- **1.0** (January 2025): Initial production specification

---

**Authors:** OdinSecure.AI  
**Contact:** [GitHub Issues](https://github.com/Maverick0351a/signet-protocol/issues)  
**License:** MIT