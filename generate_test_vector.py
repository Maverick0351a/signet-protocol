import sys
sys.path.append('server')
from utils.jcs import canonicalize
import json
import hashlib

# Create a proper receipt
receipt = {
    "trace_id": "test-basic-001",
    "hop": 1,
    "ts": "2025-01-27T12:00:00Z",
    "cid": "sha256:abc123def456789012345678901234567890123456789012345678901234567890",
    "canon": '{"amount":1000,"currency":"USD","invoice_id":"INV-001"}',
    "algo": "sha256",
    "prev_receipt_hash": None,
    "policy": {
        "engine": "HEL",
        "allowed": True,
        "reason": "ok"
    },
    "tenant": "test"
}

# Calculate the correct receipt hash
receipt_copy = receipt.copy()
receipt_copy.pop("receipt_hash", None)
canonical = canonicalize(receipt_copy)
receipt_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
receipt["receipt_hash"] = receipt_hash

print("Correct receipt:")
print(json.dumps(receipt, indent=2))
