# Export Bundle Walkthrough

Step-by-step guide to export and verify a receipt chain.

## 1. Execute Exchange
```bash
curl -X POST https://signet-protocol.fly.dev/v1/exchange \
  -H "X-SIGNET-API-Key: YOUR_KEY" \
  -H "X-SIGNET-Idempotency-Key: demo-001" \
  -H "Content-Type: application/json" \
  -d '{"payload_type":"openai.tooluse.invoice.v1","target_type":"invoice.iso20022.v1","payload":{"tool_calls":[{"type":"function","function":{"name":"create_invoice","arguments":"{\\"invoice_id\\":\\"INV-1\\",\\"amount\\":1000,\\"currency\\":\\"USD\\"}"}}]}}'
```

Grab `X-SIGNET-Trace` from response.

## 2. Export Chain
```bash
TRACE=... # trace id
curl -i https://signet-protocol.fly.dev/v1/receipts/export/$TRACE > export.json
```
Headers: `X-ODIN-Response-CID`, `X-ODIN-Signature`, `X-ODIN-KID`.

## 3. Verify (Python SDK)
```python
import json
from signet_verify import verify_export_bundle
bundle=json.load(open('export.json'))
ok,reason=verify_export_bundle(bundle,'https://signet-protocol.fly.dev/.well-known/jwks.json')
print(ok,reason)
```

## 4. Manual CID Check
```bash
cat export.json | jq '{trace_id,chain,exported_at}' > core.json
python - <<'PY'
import json,hashlib
o=json.load(open('core.json'))
canonical=json.dumps(o, separators=(',',':'), sort_keys=True)
print('sha256:'+hashlib.sha256(canonical.encode()).hexdigest())
PY
```

## 5. Failure Modes
| Failure | Cause | Mitigation |
|---------|-------|------------|
| Invalid bundle CID | Modified JSON / different serialization | Re-export |
| Invalid signature | Wrong key / tamper | Refresh JWKS & retry |
| Broken chain | Missing receipt order | Rebuild / inspect storage |

Integrate into UI: Export → show CID/signature badges → client verify.
