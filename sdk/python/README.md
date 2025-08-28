# Signet Protocol - Python Verification SDK

[![PyPI version](https://badge.fury.io/py/signet-verify.svg)](https://badge.fury.io/py/signet-verify)
[![Verified against SR-1 test vectors](https://img.shields.io/badge/SR--1-verified-green)](../../test-vectors/)

Verify Signet Protocol receipts and chains in 5 lines of code.

## Quick Start

### Installation

```bash
pip install signet-verify
```

### Verify a Receipt (One-liner)

```python
from signet_verify import verify_receipt

# Verify any receipt in one line
valid, reason = verify_receipt(receipt_data)
print(f"Valid: {valid}, Reason: {reason}")
```

### Verify a Receipt Chain

```python
from signet_verify import verify_chain

# Verify complete audit trail
receipts = [receipt1, receipt2, receipt3]  # Chronological order
valid, reason = verify_chain(receipts)
print(f"Chain valid: {valid}, Reason: {reason}")
```

### Verify Export Bundle with Signatures

```python
from signet_verify import verify_export_bundle

# Verify cryptographically signed bundle
valid, reason = verify_export_bundle(
    bundle, 
    jwks_url="https://your-server/.well-known/jwks.json"
)
print(f"Bundle valid: {valid}, Reason: {reason}")
```

## Advanced Usage

### Using the Verifier Class

```python
from signet_verify import SignetVerifier

# Create verifier with custom settings
verifier = SignetVerifier(jwks_cache_ttl=7200)  # 2 hour cache

# Verify individual receipt
valid, reason = verifier.verify_receipt(receipt)

# Verify with previous receipt for chain validation
valid, reason = verifier.verify_receipt(receipt, previous_receipt)

# Verify complete chain
valid, reason = verifier.verify_chain(receipts)

# Verify signed export bundle
valid, reason = verifier.verify_export_bundle(bundle, jwks_url)
```

## API Reference

### Functions

#### `verify_receipt(receipt, previous_receipt=None)`
Verify a single Signet receipt.

**Parameters:**
- `receipt` (dict): The receipt to verify
- `previous_receipt` (dict, optional): Previous receipt in chain for linkage verification

**Returns:**
- `(bool, str)`: (is_valid, reason)

#### `verify_chain(receipts)`
Verify a complete receipt chain.

**Parameters:**
- `receipts` (list): List of receipts in chronological order

**Returns:**
- `(bool, str)`: (is_valid, reason)

#### `verify_export_bundle(bundle, jwks_url=None)`
Verify a signed export bundle.

**Parameters:**
- `bundle` (dict): The export bundle to verify
- `jwks_url` (str, optional): URL to fetch JWKS for signature verification

**Returns:**
- `(bool, str)`: (is_valid, reason)

### SignetVerifier Class

#### `__init__(jwks_cache_ttl=3600)`
Create a new verifier instance.

**Parameters:**
- `jwks_cache_ttl` (int): JWKS cache TTL in seconds (default: 1 hour)

#### Methods
- `verify_receipt(receipt, previous_receipt=None)` - Verify single receipt
- `verify_chain(receipts)` - Verify receipt chain
- `verify_export_bundle(bundle, jwks_url=None)` - Verify signed bundle

## Receipt Format

Signet receipts follow the SR-1 specification:

```json
{
  "trace_id": "unique-trace-identifier",
  "hop": 1,
  "ts": "2025-01-27T12:00:00Z",
  "cid": "sha256:content-hash",
  "canon": "{\"normalized\":\"data\"}",
  "algo": "sha256",
  "prev_receipt_hash": null,
  "policy": {
    "engine": "HEL",
    "allowed": true,
    "reason": "ok"
  },
  "tenant": "your-tenant",
  "receipt_hash": "sha256:receipt-hash"
}
```

## Validation Rules

The SDK validates:

1. **Receipt Hash Integrity** - Verifies receipt_hash matches computed hash
2. **Chain Linkage** - Ensures prev_receipt_hash links correctly
3. **Hop Sequence** - Validates hop numbers increment correctly
4. **Content Integrity** - Verifies CID matches canonicalized content
5. **Timestamp Format** - Ensures ISO 8601 timestamp format
6. **Signature Verification** - Validates Ed25519 signatures (if JWKS provided)

## Error Handling

```python
from signet_verify import verify_receipt

try:
    valid, reason = verify_receipt(receipt)
    if not valid:
        print(f"Verification failed: {reason}")
except Exception as e:
    print(f"Verification error: {e}")
```

## Test Vectors

The SDK is verified against comprehensive test vectors:

```python
import json
from signet_verify import verify_receipt

# Load test vector
with open('test-vectors/receipts/basic-receipt.json') as f:
    test_receipt = json.load(f)

# Should pass
valid, reason = verify_receipt(test_receipt)
assert valid, f"Test vector failed: {reason}"
```

## Requirements

- Python 3.7+
- `cryptography>=3.0.0` (for signature verification)
- `requests>=2.25.0` (for JWKS fetching)

## License

Apache License 2.0 - see [LICENSE](../../LICENSE) for details.

## Links

- [Signet Protocol Documentation](../../docs/)
- [SR-1 Receipt Specification](../../docs/SR-1-SIGNET-RECEIPT-SPEC.md)
- [Test Vectors](../../test-vectors/)
- [PyPI Package](https://pypi.org/project/signet-verify/)

---

**Verify receipts in 5 lines. Build trust in 1 line.** 🔗
