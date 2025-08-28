# 🔗 Signet Protocol - Trust Fabric for AI-to-AI Communications

![Tests](./badges/tests-badge.svg)
[![Production Ready](https://img.shields.io/badge/status-production%20ready-green)](#deployment)
[![Standard](https://img.shields.io/badge/standard-SR--1%20%7C%20SVX--1-blue)](#specifications)

**Middleware for secure, auditable, and verifiable AI-to-AI communications.**

The Signet Protocol establishes the **Trust Fabric** - providing cryptographic proof of AI interactions through Verified Exchanges (VEx), Signed Receipts, and HEL egress control.

## 🧩 Ecosystem Packages & Tooling

| Artifact | Status | Reference |
|----------|--------|-----------|
| VS Code Extension (Signet Lens) | Published | Marketplace: https://marketplace.visualstudio.com/items?itemName=odinsecureai.signet-lens |
| JavaScript Verification SDK (`signet-verify-js`) | Published | Package: signet-verify-js (npm) |
| Python Verification SDK (`signet-verify`) | Published | Package: signet-verify (PyPI) |
| n8n Community Node (`n8n-nodes-signet-protocol`) | Published | npm: n8n-nodes-signet-protocol |

### VS Code Extension (Signet Lens)
Add in‑editor receipt chain verification, CID diffing, bundle export, and interactive chain visualization.

Install (CLI):
```bash
code --install-extension odinsecureai.signet-lens
```
Or search "Signet Lens" in the Extensions view.

Key Commands:
* Verify Receipt Chain
* Visualize Receipt Chain
* Copy Bundle CID
* Diff CID

### JavaScript SDK
Quick verify:
```bash
npm install signet-verify-js
```
```javascript
import { verifyReceipt } from 'signet-verify-js';
const { valid, reason } = verifyReceipt(receipt);
```

### Python SDK
```bash
pip install signet-verify
```
```python
from signet_verify import verify_receipt
valid, reason = verify_receipt(receipt)
```

Both SDKs implement canonicalization + hash recomputation for offline integrity checks and bundle CID comparison.

## 🎯 Quick Start (One Line Integration)

### Python/LangChain
```python
from signet_callback import enable_signet_verification

# Enable verification in one line
signet = enable_signet_verification("http://localhost:8088", "your-api-key")
chain.run(input, callbacks=[signet])
```

### JavaScript/Browser
```javascript
import { verifyReceipt } from './sdk/javascript/signet-verify.js';

// Verify receipts in one line
const { valid, reason } = await verifyReceipt(receipt);
```

### Plain HTTP
```python
from signet_client import verify_invoice

# Verify data in one line
result = verify_invoice("http://localhost:8088", "your-api-key", invoice_data)
```

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agent A    │───▶│  Signet Protocol │───▶│   AI Agent B    │
│                 │    │                  │    │                 │
│ • Sends data    │    │ • Validates      │    │ • Receives      │
│ • Gets receipt  │    │ • Transforms     │    │   verified data │
└─────────────────┘    │ • Signs receipt  │    └─────────────────┘
                       │ • Forwards       │
                       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Audit Trail     │
                       │                  │
                       │ • Hash-chained   │
                       │ • Cryptographically│
                       │   signed         │
                       │ • Exportable     │
                       └──────────────────┘
```

### Trust Guarantees

1. **🔐 Verified Exchanges (VEx)**: Cryptographic proof that interactions occurred
2. **📋 Signed Receipts**: Immutable audit trails with hash-chained integrity
3. **🛡️ HEL Egress Control**: Policy-enforced security for outbound communications
4. **🧠 Semantic Invariants**: Prevents LLM corruption of critical business data

## 🚀 Features

### ✅ Production-Ready Security
- **SSRF Protection**: Complete validation of outbound requests
- **IP Pinning**: Prevents DNS rebinding attacks  
- **Response Size Limits**: Memory exhaustion protection
- **Input Validation**: Enhanced schema validation with fallback

### ✅ Enterprise Billing
- **Token-Level Metering**: Precise billing for AI service usage
- **Reserved Capacity**: Enterprise-grade billing with commitments
- **Tiered Pricing**: Flexible pricing models for different usage levels
- **Stripe Integration**: Production billing system

### ✅ Scalable Infrastructure  
- **PostgreSQL Support**: Production-grade database backend
- **Connection Pooling**: Efficient database resource management
- **Prometheus Metrics**: Comprehensive monitoring (expanded core & billing metrics)
- **Multi-tenant Architecture**: Secure tenant isolation

### ✅ Standards Compliance
- **RFC 8785 JCS**: JSON Canonicalization Scheme compliance
- **Ed25519 Signatures**: Cryptographic receipt signing
- **JWKS Support**: Public key distribution
- **Export Bundles**: Signed audit trail exports

## 📊 Current Status

**🎉 All Tests Passing (52 + 1 skipped) – Production Hardened Build**

```bash
pytest tests/ -v
# =============================== 52 passed, 1 skipped, 6 warnings in ~7.6s ===============================
```

- ✅ **52 tests passing, 1 skipped**
- ✅ **Server running** and healthy on port 8088
- ✅ **Core + billing + observability features** implemented (see roadmap for upcoming refinements)
- ✅ **Production deployment** ready with comprehensive guides

## 🛠️ Installation & Setup

### 1. Clone and Install
```bash
git clone https://github.com/Maverick0351a/signet-protocol
cd signet-protocol
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy production template
cp .env.production .env

# Edit with your secrets
# - OpenAI API key for fallback repair
# - Stripe API key for billing
# - PostgreSQL URL for production storage
# - Private key for receipt signing
```

### 3. Start Server
```bash
# Development
uvicorn server.main:app --reload --port 8088

# Production  
uvicorn server.main:app --host 0.0.0.0 --port 8088 --workers 4

### 3a. Run with Docker (optional)
```bash
docker build -t signet .
docker run -p 8088:8088 \
  -e SP_API_KEYS='{"demo_key":{"tenant":"acme","fallback_enabled":true}}' \
  signet
```

### 3b. docker-compose (Prometheus + Grafana example)
```bash
docker compose up -d
```
```

### 4. Verify Health
```bash
curl http://localhost:8088/healthz
# {"ok":true,"storage":"sqlite","ts":"2025-01-27T21:59:41Z"}
```

## ☁️ Hosted Instance (Fly.io)

You can point clients or the n8n node at the deployed instance:

Base URL: `https://signet-protocol.fly.dev`

Key Endpoints:
```text
Health:   https://signet-protocol.fly.dev/healthz
API Docs: https://signet-protocol.fly.dev/docs
JWKS:     https://signet-protocol.fly.dev/.well-known/jwks.json
Metrics:  https://signet-protocol.fly.dev/metrics (if exposed)
```

Example exchange request (replace YOUR_KEY):
```bash
curl -X POST https://signet-protocol.fly.dev/v1/exchange \
  -H "X-SIGNET-API-Key: YOUR_KEY" \
  -H "X-SIGNET-Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_type": "openai.tooluse.invoice.v1",
    "target_type": "invoice.iso20022.v1",
    "payload": {"tool_calls": []}
  }'
```

For n8n, set the credential "Signet URL" to `https://signet-protocol.fly.dev`.

## 📚 Documentation

### Specifications
- **[SR-1: Signet Receipt Specification](./docs/SR-1-SIGNET-RECEIPT-SPEC.md)** - Receipt format and validation
- **[SVX-1: Verified Exchange Specification](./docs/SVX-1-VERIFIED-EXCHANGE-SPEC.md)** - Exchange semantics and billing
- **[Trust Fabric Standard](./docs/TRUST-FABRIC-STANDARD.md)** - Strategic positioning and adoption

### Guides
- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[Advanced Features](./ADVANCED_FEATURES.md)** - Detailed feature documentation
- **[API Documentation](http://localhost:8088/docs)** - Interactive API docs (when server running)
- **[Stable API Spec v1.0.0](./docs/api/openapi-v1.0.0.yaml)** - Frozen OpenAPI snapshot
- **[Error Glossary](./docs/ERROR_GLOSSARY.md)** - Standard errors & headers
- **[Export Bundle Walkthrough](./docs/EXPORT_BUNDLE_WALKTHROUGH.md)** - Signed chain verification steps

### SDKs & Tools
- **[Python Verification SDK](./sdk/python/signet_verify.py)** - Verify receipts in 5 lines
- **[JavaScript Verification SDK](./sdk/javascript/signet-verify.js)** - Browser/Node.js verification
- **[Python Client SDK](./sdk/python/signet_client.py)** - Simple HTTP client
- **[LangChain Adapter](./adapters/langchain/signet_callback.py)** - One-line LangChain integration
- **[CLI Tools](./tools/signet_cli.py)** - Mapping and policy utilities

## 🔧 API Usage

The canonical, versioned specification for clients is published under `docs/api/` (e.g. `openapi-v1.0.0.yaml`). The root `openapi.yaml` may advance ahead of released versions; rely on a frozen spec file for generated clients.

### Basic Exchange
```bash
curl -X POST http://localhost:8088/v1/exchange \
  -H "X-SIGNET-API-Key: demo_key" \
  -H "X-SIGNET-Idempotency-Key: unique-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_type": "openai.tooluse.invoice.v1",
    "target_type": "invoice.iso20022.v1", 
    "payload": {
      "tool_calls": [{
        "type": "function",
        "function": {
          "name": "create_invoice",
          "arguments": "{\"invoice_id\":\"INV-001\",\"amount\":1000,\"currency\":\"USD\"}"
        }
      }]
    },
    "forward_url": "https://your-webhook.com/receive"
  }'
```

### Response
```json
{
  "trace_id": "demo-abc-123",
  "normalized": {
    "invoice_id": "INV-001",
    "amount_minor": 100000,
    "currency": "USD"
  },
  "receipt": {
    "ts": "2025-01-27T12:00:00Z",
    "cid": "sha256:content-hash",
    "receipt_hash": "sha256:receipt-hash",
    "hop": 1
  },
  "forwarded": {
    "status_code": 200,
    "host": "your-webhook.com"
  }
}
```

## 📈 Monitoring

### Health & Observability Endpoints
- `GET /healthz` - Server health check
- `GET /metrics` - Prometheus metrics (core, billing, fallback, latency)
- `GET /.well-known/jwks.json` - Public keys for verification

### Key Metrics (Selected)
```prometheus
# Core exchange pipeline
signet_exchanges_total
signet_denied_total{reason}
signet_forward_total{host}
signet_idempotent_hits_total
signet_exchange_phase_latency_seconds_bucket{phase}
signet_exchange_total_latency_seconds_bucket

# Repair / fallback
signet_repair_attempts_total
signet_repair_success_total
signet_fallback_used_total
signet_semantic_violation_total

# Billing & usage
signet_vex_units_total
signet_fu_tokens_total
signet_billing_enqueue_total{type}
signet_reserved_capacity{tenant,type}
signet_reserved_vex_capacity{tenant}
signet_reserved_fu_capacity{tenant}
signet_overage_charges_total{tenant,type,tier}
```

OpenTelemetry spans are emitted per phase (e.g. exchange.phase.sanitize, exchange.phase.transform, exchange.phase.forward) and can be exported via OTLP by setting OTEL_EXPORTER_OTLP_ENDPOINT.

### Tracing (OpenTelemetry)
Set these environment variables to export spans:
```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=signet-protocol
```
If no endpoint is set a console exporter logs spans (development convenience).

### Dashboards

Starter Grafana dashboards are under `monitoring/grafana/dashboards`:

* `signet_observability.json` – Exchanges, denied & fallback usage, phase p95 latency, total latency, repairs, reserved capacity.
* `signet_billing.json` – Verified Exchange units, FU tokens, billing enqueue rates, denied reason distribution, forward host distribution.

Provision them by mounting the directory into Grafana and referencing the included `dashboard.yml` provider (already configured to scan the path).

### Insomnia Plugin

`tools/insomnia_plugin_signet.js` provides a template tag to verify receipts inline. Install by copying it into your Insomnia plugins folder, then use:

`{{ signetVerify <receipt_json> <jwks_url> }}`

Example JWKS URL: `http://localhost:8088/.well-known/jwks.json`

### Stripe MCP Integration

Enhanced billing endpoints (product setup, payment links, dashboard) use a simulated MCP Stripe client. See `STRIPE_MCP_INTEGRATION_GUIDE.md` and run:
```bash
curl -X POST -H "X-SIGNET-API-Key: demo_key" http://localhost:8088/v1/billing/setup-products
```

### CI Test Badge

Workflow `.github/workflows/test_badge.yml` generates `badges/tests-badge.svg` with pass/fail/skip counts. Add the badge near the top of this README:

`![Tests](./badges/tests-badge.svg)`

### Admin & Tooling

* Reload reserved capacity without restart: `POST /v1/admin/reload-reserved` (requires API key)
* Postman collection: `integrations/postman/Signet.postman_collection.json`

## 🏢 Enterprise Features

### Reserved Capacity Billing
```json
{
  "enterprise_customer": {
    "vex_reserved": 100000,
    "fu_reserved": 500000,
    "vex_overage_tiers": [
      {"threshold": 50000, "price_per_unit": 0.005}
    ]
  }
}
```

### Multi-Tenant Security
- Per-tenant API keys with allowlists
- Isolated data storage
- Configurable quotas and limits
- Comprehensive audit trails

### Production Deployment
- PostgreSQL backend for scale
- Docker containerization
- Kubernetes manifests
- Load balancer configuration
- Monitoring and alerting setup

## 🧪 Testing

### Run Test Suite
```bash
# Full suite (52 passed, 1 skipped)
pytest tests/ -v

# Specific categories
pytest tests/test_policy.py -v          # Security & IP validation
pytest tests/test_jcs.py -v             # RFC 8785 compliance  
pytest tests/test_fallback_metering.py -v # Token counting & quotas
pytest tests/test_exchange.py -v        # End-to-end API
```

### CLI Tools
### Dependency Pinning & Upgrade Policy
Selective pinning is applied to balance stability and security:
- OpenAI SDK pinned at 0.28.0 pending migration to the 1.x interface.
- OpenTelemetry stack pinned at 1.25.0 (instrumentation 0.46b0) until coordinated upgrade (ensures span attribute compatibility).
- FastAPI / Starlette / Pydantic held at tested versions; a future batch upgrade will advance them together.
- Safe minor bumps (requests, python-dotenv, fastjsonschema, prometheus-client) applied proactively.
Automated update PRs are generated weekly via Dependabot (pip + npm) with majors for sensitive packages ignored until manual review.

### n8n Community Node
Install the published community node to orchestrate Signet exchanges inside workflows:
```bash
npm install n8n-nodes-signet-protocol
```
Operations included: create exchange, get receipt chain, export bundle, billing dashboard, reload reserved capacity, create payment link. Configure the credential with your Signet base URL and API key.

```bash
# Test mapping transformations
python tools/signet_cli.py map test --mapping mapping.json --sample data.json

# Validate policy configuration  
python tools/signet_cli.py policy lint --allowlist "api.example.com" --check-dns

# Validate schemas
python tools/signet_cli.py schema validate --input-schema schema.json --data sample.json
```

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start development server
uvicorn server.main:app --reload --port 8088
```

### Linting & Formatting
Ruff is configured in `pyproject.toml` and enforced in CI (`lint` workflow). Pull requests must be clean; direct pushes to `main` will auto-apply safe fixes & formatting and commit them.
Run locally:
```bash
ruff check .
ruff format .  # (optional) apply formatting
```
Adjust rule selection or ignores in `[tool.ruff]` as standards evolve.

### Standards Compliance
- Follow SR-1 receipt specification
- Implement SVX-1 exchange semantics  
- Maintain RFC 8785 JCS compliance
- Add comprehensive test coverage

## 📄 License

Licensed under the Apache License, Version 2.0. See [LICENSE](./LICENSE).

Software is provided "AS IS" without warranties; evaluate security & compliance against your own threat model before production use.

## 🔗 Links

- **Documentation**: [Comprehensive guides and specifications](./docs/)
- **API Docs**: http://localhost:8088/docs (when server running)
- **Metrics**: http://localhost:8088/metrics
- **Health**: http://localhost:8088/healthz

---

**The Signet Protocol: Building the Trust Fabric for AI-to-AI Communications** 🚀

*Ready for production deployment with enterprise-grade security, billing, and monitoring.*
