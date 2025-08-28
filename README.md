# <div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/LogoSignet.png">
    <source media="(prefers-color-scheme: light)" srcset="./assets/LogoSignet-light.png, ./assets/LogoSignet.png 2x">
    <img src="./assets/LogoSignet.png" alt="Signet Protocol Logo" width="360" />
  </picture>
</div>

# Signet Protocol

Secure, verifiable, auditable AI-to-AI exchanges ("Trust Fabric"). Signet issues signed receipts and hash‑chained audit trails for every normalized transformation and optional forward delivery.

![Tests](./badges/tests-badge.svg) [![Status](https://img.shields.io/badge/status-production-green)](#quick-start) [![Spec](https://img.shields.io/badge/spec-v1.0.0-blue)](./docs/api/openapi-v1.0.0.yaml)

---
## What You Get

| Capability | What It Solves |
|------------|----------------|
| Verified Exchanges (VEx) | Cryptographic proof an interaction occurred & wasn’t tampered |
| Signed Receipts | Immutable, hash‑linked audit history |
| Policy + HEL Egress Control | Stops unsafe outbound calls (SSRF, DNS rebinding) |
| Semantic Invariant Guardrails | Prevents model corruption of key fields |
| Export Bundles | Portable chain for compliance / forensics |
| Prometheus + Tracing | Production visibility out of the box |
| Billing & Quotas | Token + unit metering, reserved capacity, Stripe integration |

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
