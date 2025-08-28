# Signet Protocol Test Vectors

This directory contains comprehensive test vectors for validating Signet Protocol implementations against the SR-1 specification.

## Structure

- `receipts/` - Individual receipt test cases
- `chains/` - Receipt chain test cases  
- `exports/` - Export bundle test cases
- `jcs/` - JSON Canonicalization Scheme test cases
- `signatures/` - Cryptographic signature test cases

## Usage

### Python
```python
from signet_verify import verify_receipt, verify_chain
import json

# Load test vector
with open('test-vectors/receipts/basic-receipt.json') as f:
    receipt = json.load(f)

# Verify
valid, reason = verify_receipt(receipt)
assert valid, f"Test vector failed: {reason}"
```

### JavaScript
```javascript
import { verifyReceipt } from '@signet/verify-js';
import receipt from './test-vectors/receipts/basic-receipt.json';

const { valid, reason } = await verifyReceipt(receipt);
console.assert(valid, `Test vector failed: ${reason}`);
```

## Test Categories

1. **Basic Receipts** - Simple valid receipts
2. **Chain Validation** - Multi-hop receipt chains
3. **Edge Cases** - Boundary conditions and error cases
4. **JCS Compliance** - RFC 8785 canonicalization tests
5. **Signature Verification** - Ed25519 signature validation
6. **Export Bundles** - Signed bundle verification

## CI Integration

Use these test vectors in your CI pipeline:

```bash
# Verify against all test vectors
npx signet-cli verify test-vectors/ --jwks https://your-server/.well-known/jwks.json
