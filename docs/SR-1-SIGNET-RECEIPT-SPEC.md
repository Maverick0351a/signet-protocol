# SR-1: Signet Receipt Specification v1.0

## Abstract

The Signet Receipt (SR-1) specification defines a cryptographically verifiable record format for AI-to-AI communications, enabling auditability, non-repudiation, and trust verification in autonomous agent systems.

## 1. Overview

A Signet Receipt provides cryptographic proof that:
- A specific payload was processed and transformed
- The transformation followed declared policies
- The result was forwarded to authorized endpoints
- All operations occurred at a specific time with full traceability

## 2. Receipt Structure

### 2.1 Core Fields

```json
{
  "trace_id": "string",           // Unique identifier for the exchange chain
  "hop": "integer",               // Sequential hop number in the chain
  "ts": "ISO8601",               // RFC3339 timestamp (UTC)
  "tenant": "string",            // Tenant identifier
  "cid": "sha256:hex",           // Content identifier of normalized payload
  "canon": "string",             // JCS-canonicalized payload
  "algo": "sha256",              // Hash algorithm used
  "prev_receipt_hash": "string", // Hash of previous receipt (null for first)
  "receipt_hash": "string",      // Hash of this receipt
  "policy": {                    // Policy evaluation result
    "engine": "HEL",
    "allowed": "boolean",
    "reason": "string"
  }
}
```

### 2.2 Extended Fields (Optional)

```json
{
  "forwarded": {                 // Present if forwarding occurred
    "url": "string",
    "status_code": "integer",
    "host": "string",
    "pinned_ip": "string",
    "response_size": "integer"
  },
  "fallback_used": "boolean",    // True if LLM repair was used
  "fu_tokens": "integer",        // Fallback tokens consumed
  "semantic_violations": ["string"] // Failed invariant checks
}
```

## 3. Canonicalization (JCS)

### 3.1 Requirements

Signet Receipts MUST use RFC 8785 JSON Canonicalization Scheme (JCS) with:

- **Unicode NFC Normalization**: All strings normalized to Unicode NFC form
- **Deterministic Key Ordering**: Object keys sorted lexicographically
- **Minimal Whitespace**: No unnecessary spaces, newlines, or tabs
- **Consistent Number Format**: Integers without decimals, floats with minimal precision

### 3.2 Content Identifier (CID)

```
cid = "sha256:" + hex(sha256(jcs_canonicalize(payload)))
```

### 3.3 Receipt Hash

```
receipt_hash = "sha256:" + hex(sha256(jcs_canonicalize(receipt_without_hash)))
```

## 4. Chain Integrity

### 4.1 Chain Rules

1. **Genesis Receipt**: `prev_receipt_hash` is `null`
2. **Subsequent Receipts**: `prev_receipt_hash` MUST equal the `receipt_hash` of the previous receipt
3. **Hop Sequence**: `hop` MUST increment by 1 from previous receipt
4. **Trace Consistency**: `trace_id` MUST remain constant within a chain

### 4.2 Conflict Detection

Implementations MUST reject receipts that would create:
- Duplicate hop numbers within a trace
- Invalid previous hash references
- Non-sequential hop progression

## 5. Verification

### 5.1 Receipt Verification Algorithm

```python
def verify_receipt(receipt, previous_receipt=None):
    # 1. Verify receipt hash
    computed_hash = compute_receipt_hash(receipt)
    if receipt["receipt_hash"] != computed_hash:
        return False, "Invalid receipt hash"
    
    # 2. Verify chain linkage
    if previous_receipt:
        if receipt["prev_receipt_hash"] != previous_receipt["receipt_hash"]:
            return False, "Broken chain linkage"
        if receipt["hop"] != previous_receipt["hop"] + 1:
            return False, "Invalid hop sequence"
    
    # 3. Verify content identifier
    computed_cid = compute_cid(receipt["canon"])
    if receipt["cid"] != computed_cid:
        return False, "Invalid content identifier"
    
    return True, "Valid"
```

### 5.2 Chain Verification

```python
def verify_chain(receipts):
    if not receipts:
        return True, "Empty chain"
    
    # Verify genesis
    if receipts[0]["prev_receipt_hash"] is not None:
        return False, "Invalid genesis receipt"
    
    # Verify each receipt and linkage
    for i, receipt in enumerate(receipts):
        prev = receipts[i-1] if i > 0 else None
        valid, reason = verify_receipt(receipt, prev)
        if not valid:
            return False, f"Receipt {i}: {reason}"
    
    return True, "Valid chain"
```

## 6. Export Bundle Format

### 6.1 Signed Export Structure

```json
{
  "trace_id": "string",
  "chain": [/* array of receipts */],
  "exported_at": "ISO8601",
  "bundle_cid": "sha256:hex",
  "signature": "base64",
  "kid": "string"
}
```

### 6.2 Signature Generation

```
bundle_canonical = jcs_canonicalize({
  "trace_id": trace_id,
  "chain": chain,
  "exported_at": exported_at
})
bundle_cid = "sha256:" + hex(sha256(bundle_canonical))
signature = base64(ed25519_sign(private_key, bundle_cid))
```

## 7. Security Considerations

### 7.1 Hash Algorithm Requirements

- MUST use SHA-256 for all hash operations
- MUST use Ed25519 for digital signatures
- Key rotation MUST be supported via JWKS

### 7.2 Timestamp Validation

- Timestamps MUST be in UTC
- Implementations SHOULD reject receipts with timestamps too far in the future
- Clock skew tolerance SHOULD be configurable (default: 5 minutes)

### 7.3 Chain Length Limits

- Implementations SHOULD limit chain length to prevent DoS attacks
- Recommended maximum: 1000 receipts per trace

## 8. Implementation Requirements

### 8.1 MUST Requirements

- JCS canonicalization per RFC 8785
- SHA-256 hash algorithm
- Ed25519 signature algorithm
- Chain integrity validation
- Export bundle generation

### 8.2 SHOULD Requirements

- JWKS endpoint for public key distribution
- Configurable timestamp validation
- Chain length limits
- Concurrent access protection

### 8.3 MAY Requirements

- Alternative hash algorithms (with negotiation)
- Compressed export formats
- Batch verification optimizations

## 9. IANA Considerations

This specification defines:
- Media type: `application/vnd.signet.receipt+json`
- URI scheme: `signet:` for receipt references
- Well-known URI: `/.well-known/signet-jwks.json`

## 10. References

- RFC 8785: JSON Canonicalization Scheme (JCS)
- RFC 8037: CFRG Elliptic Curve Diffie-Hellman (ECDH) and Signatures in JSON Object Signing and Encryption (JOSE)
- RFC 7517: JSON Web Key (JWK)

---

**Status**: Draft Specification  
**Version**: 1.0  
**Date**: 2025-01-27  
**Authors**: Signet Protocol Contributors
