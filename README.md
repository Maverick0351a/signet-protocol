Signet Protocol

Secure, verifiable, auditable AI-to-AI exchanges ("Trust Fabric"). Signet issues signed receipts and hash‑chained audit trails for every normalized transformation and optional forward delivery.

**🆕 NEW: AI Act Compliance Kit** - Turn cryptographic receipts into ready-made conformity dossiers (EU AI Act / NIST AI RMF / ISO 42001) with one-click technical documentation, post-market monitoring, and regulator export bundles.

![Tests](./badges/tests-badge.svg) [![Status](https://img.shields.io/badge/status-production-green)](#quick-start) [![Spec](https://img.shields.io/badge/spec-v1.0.0-blue)](./docs/api/openapi-v1.0.0.yaml) [![Compliance](https://img.shields.io/badge/compliance-AI_Act_Ready-brightgreen)](#ai-act-compliance-kit)

> ⭐ If this helps you build safer AI systems, please **Star** the repo — it signals demand and unlocks more OSS investment.

---
## Repository Layout (Key Paths)

```
signet-protocol/
├─ server/
│  ├─ rtl/                # Transparency log (Merkle tree, STH signer)
│  ├─ forward/pch.py      # Proof-Carrying HTTP (signed outbound headers)
│  ├─ identity/           # DID document & pluggable signer (software / hw)
│  └─ ...                 # FastAPI app & pipeline modules
├─ sdk/
│  ├─ node/pch-express/   # Express middleware verifying PCH signatures
│  ├─ python/signet_pch_fastapi/ # FastAPI middleware for PCH verification
│  └─ wasm/verify/        # WASM receipt / Merkle proof verifier
├─ specs/                 # Draft feature specifications
│  ├─ RTL-1-TRANSPARENCY-LOG.md
│  ├─ PCH-1-PROOF-CARRYING-HTTP.md
│  └─ DID-1-KEY-BINDING.md
├─ tools/
│  ├─ signet_cli.py       # General CLI
│  └─ signet_rtl_cli.py   # Transparency log proof fetch & verify
└─ vscode-extension/      # Signet Lens (receipt visualization)
```

Specs capture evolving cryptographic / interoperability contracts; implementations may have placeholder algorithms (e.g., current PCH HMAC placeholder → upcoming Ed25519/JWS upgrade).

---
## AI Act Compliance Kit

**Transform cryptographic receipts into ready-made conformity dossiers** for EU AI Act, NIST AI RMF, and ISO 42001 compliance.

### One-Click Technical Documentation
```bash
# Generate complete AI Act Annex IV dossier
curl -H "X-SIGNET-API-Key: demo_key" \
  http://localhost:8088/v1/compliance/annex-iv/my-system?format=json

# Export for regulators with cryptographic integrity
curl -X POST -H "X-SIGNET-API-Key: demo_key" \
  http://localhost:8088/v1/compliance/retention/export \
  -d '{"profile_name": "general_audit", "date_range": {"start": "2024-01-01T00:00:00Z", "end": "2024-12-31T23:59:59Z"}}'
```

### Compliance Modules
| Module | Purpose | AI Act Coverage |
|--------|---------|-----------------|
| **Annex IV Generator** | Technical documentation dossier | Articles 11, 47-48 |
| **Retention Manager** | 10-year data retention & regulator exports | Article 12 |
| **Post-Market Monitoring** | Performance drift detection & PMM reports | Article 61 |
| **Risk Manager** | NIST AI RMF compliance & risk assessment | Article 9 |
| **CE Marking Generator** | EU conformity assessment & declaration | Articles 47-48 |
| **GPAI Transparency** | General Purpose AI disclosures | GPAI obligations |

### Key Benefits
- **Procurement Unblocker**: Answer RFP questions with signed evidence, not promises
- **Sales Acceleration**: Pre-built dossiers reduce legal review cycles by 20-40%
- **Verifiable Evidence**: Cryptographically signed proofs that auditors can independently verify
- **Cross-Standard Coverage**: One implementation covers AI Act, NIST AI RMF, and ISO 42001
- **Automated Monitoring**: Real-time drift detection and compliance status tracking

### Quick Demo
```python
# Get unified compliance dashboard
import requests
headers = {'X-SIGNET-API-Key': 'demo_key'}
dashboard = requests.get('http://localhost:8088/v1/compliance/dashboard', headers=headers).json()
print(f"Compliance status: {dashboard['retention_status']['compliant']}")

# Generate PMM report
pmm_report = requests.post('http://localhost:8088/v1/compliance/pmm-report', 
  headers=headers, 
  json={
    "system_id": "my-ai-system",
    "start_date": "2024-01-01T00:00:00Z", 
    "end_date": "2024-12-31T23:59:59Z"
  }).json()
```

**📖 Full Documentation**: See [`docs/COMPLIANCE_FEATURES.md`](./docs/COMPLIANCE_FEATURES.md) for complete API reference and regulatory mapping.

---
## Why Signet?
| Problem Without Signet | With Signet |
|------------------------|-------------|
| Opaque AI tool calls / prompt chains | Cryptographically signed, replayable trail |
| Hard to prove no tampering | Hash‑linked receipts (detect single‑byte mutation) |
| Ad‑hoc logging (no integrity) | Canonical JSON + deterministic hashing (RFC 8785) |
| Unbounded egress risk (SSRF, data exfil) | HEL policy + allowlist + IP pinning |
| "Trust me" billing | Unit & token metering + exportable billing evidence |
| Post‑incident forensic gaps | Export bundle: portable ground truth chain |

---
## Top Use Cases
| Use Case | Benefit |
|----------|---------|
| Multi-agent orchestration | Prove which agent produced which transformed fields |
| Regulated data workflows (fintech, healthcare) | Immutable audit for compliance & dispute resolution |
| Usage-based AI billing platforms | Transparent, verifiable unit attribution |
| Supply chain / output provenance | Attest each normalization / enrichment hop |
| Security boundary enforcement | Prevent unauthorized outbound calls & data leakage |
| Failure & drift analysis | Compare historical, signed normalized outputs over time |

---
## 30‑Second Tour
```mermaid
flowchart LR
A[Raw AI Tool Output] --> N[Normalize & Canonicalize]\n(schema + invariants)
N --> R[Signed Receipt]\n(Ed25519)
R --> C[Chain Storage]\n(Hash link)
R -->|optional forward| F[Webhook / Downstream]
C --> E[Export Bundle]\n(Forensics / Billing)
```

```python
# 1. Submit exchange
res = requests.post('/v1/exchange', json=payload, headers=auth)
receipt = res.json()['receipt']

# 2. Export later
bundle = requests.post('/v1/export/bundle', json={'trace_id': res.json()['trace_id']}, headers=auth).json()

# 3. Offline verify
from signet_verify import verify_receipt
all_ok = all(verify_receipt(r)[0] for r in bundle['receipts'])
```

```js
// Browser / Node receipt verification
import { verifyReceipt } from 'signet-verify-js';
const { valid } = verifyReceipt(receipt); // true if signature & hash chain hold
```

---
## Extended Examples
### A. End-to-End (Python)
```python
import requests, json
API = 'http://localhost:8088'
H = {
  'X-SIGNET-API-Key': 'demo_key',
  'X-SIGNET-Idempotency-Key': 'demo-001',
  'Content-Type': 'application/json'
}
payload = {
  'payload_type': 'openai.tooluse.invoice.v1',
  'target_type': 'invoice.iso20022.v1',
  'payload': { 'tool_calls': [] }
}
# Exchange
x = requests.post(f'{API}/v1/exchange', headers=H, json=payload).json()
print('Normalized amount:', x['normalized'].get('amount_minor'))
# Export chain
bundle = requests.post(f'{API}/v1/export/bundle', headers=H, json={'trace_id': x['trace_id']}).json()
print('Receipts in chain:', len(bundle['receipts']))
```

### B. Tamper Detection (Illustrative)
If an attacker flips a digit inside a recorded normalized field:
```python
from copy import deepcopy
from signet_verify import verify_receipt
r = bundle['receipts'][0]
print(verify_receipt(r))  # (True, None)
mut = deepcopy(r)
mut['normalized']['amount_minor'] = 999999  # tamper
print(verify_receipt(mut))  # (False, 'hash mismatch')
```
A single‑field mutation alters the canonical serialization hash; verification fails immediately.

### C. LangChain Integration
```python
from signet_callback import enable_signet_verification
signet = enable_signet_verification(API, 'demo_key')
result = chain.run("make invoice", callbacks=[signet])
```

---
## Trust Fabric Concepts (Plain Language)
| Term | Plain Meaning |
|------|---------------|
| VEx (Verified Exchange) | A single normalized + signed step in a multi-hop chain |
| Receipt | JSON envelope: content CID, previous hash, signature, timestamp |
| Bundle | Exported ordered list of receipts (plus root metadata) |
| Semantic Invariant | Rule that critical fields must not structurally change |
| HEL Policy | Outbound network policy (host / method / size / timeout) |

---
## Quick Start (3 Paths)

### 1. Run Locally (Python)
```bash
git clone https://github.com/Maverick0351a/signet-protocol
cd signet-protocol
pip install -r requirements.txt
uvicorn server.main:app --port 8088
```
Health check:
```bash
curl http://localhost:8088/healthz
```

### 2. Docker
```bash
docker build -t signet .
docker run -p 8088:8088 -e SP_API_KEYS='{"demo_key":{"tenant":"acme","fallback_enabled":true}}' signet
```

### 3. Hosted Demo (Fly.io)
Base URL: `https://signet-protocol.fly.dev`

---
## Make an Exchange
```bash
curl -X POST http://localhost:8088/v1/exchange \
  -H "X-SIGNET-API-Key: demo_key" \
  -H "X-SIGNET-Idempotency-Key: unique-123" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_type": "openai.tooluse.invoice.v1",
    "target_type": "invoice.iso20022.v1",
    "payload": {"tool_calls": []}
  }'
```
Response (trimmed):
```json
{
  "trace_id": "demo-abc-123",
  "normalized": {"invoice_id": "INV-001"},
  "receipt": {"hop":1,"cid":"sha256:...","receipt_hash":"sha256:..."}
}
```

---
## Verify a Receipt (SDKs)

JavaScript:
```bash
npm install signet-verify-js
```
```js
import { verifyReceipt } from 'signet-verify-js';
const { valid } = verifyReceipt(receipt);
```
Python:
```bash
pip install signet-verify
```
```python
from signet_verify import verify_receipt
valid, reason = verify_receipt(receipt)
```
LangChain (one‑liner callback):
```python
from signet_callback import enable_signet_verification
signet = enable_signet_verification("http://localhost:8088", "demo_key")
chain.run("example", callbacks=[signet])
```

---
## VS Code Extension (Signet Lens)
Visualize & diff receipt chains directly in the editor.
```bash
code --install-extension odinsecureai.signet-lens
```
Commands: Verify Receipt Chain • Visualize Chain • Copy Bundle CID • Diff CID

---
## Generated API Clients
Frozen spec snapshots live in `docs/api/` (e.g. `openapi-v1.0.0.yaml`).

Publish flows (automated):
- TypeScript npm: tag `client-ts-vX.Y.Z`
- Python PyPI: tag `client-py-vX.Y.Z`

Generate locally:
```bash
./scripts/generate_clients.sh 1.0.0
```
Details: `clients/README.md`.

---
## Key Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /healthz` | Liveness check |
| `GET /metrics` | Prometheus metrics |
| `GET /.well-known/jwks.json` | Public keys |
| `POST /v1/exchange` | Submit + normalize + sign |
| `POST /v1/export/bundle` | Export signed chain |
| `POST /v1/admin/reload-reserved` | Reload billing config |

---
## Security & Integrity Highlights
- RFC 8785 JSON canonicalization (stable hashing)
- Ed25519 signatures with published JWKS
- Idempotency keys prevent accidental replays
- SSRF & DNS rebinding defenses (IP pinning, allowlists)
- Size & time limits for outbound fetches
- Semantic invariant validation (rejects mutated critical fields)

---
## Observability
Prometheus metrics & OpenTelemetry spans are enabled by default.
Enable tracing export:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=signet-protocol
```
Sample metrics (names may evolve):
```
signet_exchanges_total
signet_exchange_total_latency_seconds_bucket
signet_repair_attempts_total
signet_vex_units_total
signet_fu_tokens_total
```
Starter Grafana dashboards: `monitoring/grafana/`.

---
## Billing (Optional)
- Verified Exchange units (VEx) + Fallback Unit tokens (FU)
- Reserved capacity per tenant
- Stripe integration for product & link setup (`/v1/billing/*` endpoints)

To enable billing locally provide API keys and run setup script (see `STRIPE_MCP_INTEGRATION_GUIDE.md`).

---
## Export & Offline Verification
Export a chain:
```bash
curl -X POST http://localhost:8088/v1/export/bundle \
  -H "X-SIGNET-API-Key: demo_key" -d '{"trace_id": "demo-abc-123"}' -o bundle.json
```
Verify offline using JS or Python SDK: load each receipt, canonicalize, recompute hash, match chain.

---
## Documentation Map
| Topic | Location |
|-------|----------|
| Receipt Spec | `docs/SR-1-SIGNET-RECEIPT-SPEC.md` |
| Verified Exchange Spec | `docs/SVX-1-VERIFIED-EXCHANGE-SPEC.md` |
| Trust Fabric Overview | `docs/TRUST-FABRIC-STANDARD.md` |
| Deployment | `DEPLOYMENT_GUIDE.md` |
| Advanced Features | `ADVANCED_FEATURES.md` |
| Branding | `docs/BRANDING.md` |
| Developer Internals | `DEVELOPERS.md` |

---
## Production Readiness Checklist
| Item | Status |
|------|--------|
| Canonical JSON receipt spec frozen (v1.0.0) | ✅ |
| End-to-end tests (52 pass) | ✅ |
| Metrics & tracing instrumentation | ✅ |
| Export bundle & offline verify | ✅ |
| Billing & reserved capacity | ✅ |
| LangChain & SDK verification libs | ✅ |
| Security controls (SSRF / IP pinning / invariants) | ✅ |
| Fallback repair + semantic guardrails | ✅ |
| Frozen OpenAPI for client generation | ✅ |

---
## Contributing
Issues & PRs welcome. See `DEVELOPERS.md` for workflows, lint, release tags.
Quick dev loop:
```bash
pip install -r requirements.txt
pytest tests/ -q
uvicorn server.main:app --reload --port 8088
```

---
## License
Apache 2.0 (see `LICENSE`).

---
Building the Trust Fabric for AI systems.
