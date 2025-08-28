# Error Glossary

Common HTTP responses and reasons emitted by the Signet Protocol server (current MVP).

## Status Codes

| HTTP | Reason / Detail Prefix | When It Occurs | Counts VEx? |
|------|------------------------|----------------|-------------|
| 200  | ok                     | Successful exchange; receipt stored | ✅ |
| 400  | missing idempotency header | X-SIGNET-Idempotency-Key absent | ❌ |
| 401  | missing api key header / invalid api key | Missing or unknown API key | ❌ |
| 403  | HEL policy denial reason | Forward URL not in tenant + global allowlists | ❌ |
| 409  | chain conflict          | Concurrent append race detected | ❌ |
| 422  | missing payload_type/target_type/payload | Required fields absent | ❌ |
| 422  | unsupported mapping in MVP | Payload/target types other than invoice demo | ❌ |
| 422  | input schema invalid: ... | Source schema validation failed | ❌ |
| 422  | arguments parse/repair failed: ... | Function.arguments could not be parsed or repaired | ❌ |
| 422  | normalized schema invalid: ... | Output schema validation failed | ❌ |
| 422  | Fallback repair violated semantic invariants: ... | Repair changed protected semantics | ❌ |
| 429  | Fallback quota exceeded: ... | FU quota would be exceeded | ❌ |

## Headers

| Header | Meaning |
|--------|---------|
| X-SIGNET-Trace / X-ODIN-Trace | Trace ID for the exchange / receipt chain |
| X-SIGNET-Idempotency-Hit      | Present ("1") when cached idempotent response returned |
| X-ODIN-Response-CID           | CID of exported bundle (export endpoint) |
| X-ODIN-Signature              | Ed25519 signature over bundle CID |
| X-ODIN-KID                    | Key ID used to sign export |

## Fallback & Semantic Invariants

If fallback repair succeeds: receipt includes `fallback_used: true` and `fu_tokens`.
If semantic invariants fail: 422 response with `semantic_violations` (no VEx counted).

## Planned Additions

| Category | Planned Detail |
|----------|----------------|
| Rate limiting | 429 RATE_LIMIT code |
| Auth scopes | 403 SCOPES_MISSING |
| Mapping registry | Refined 422 codes per mapping error |

---
Keep frontend error handling table synced with this file.
