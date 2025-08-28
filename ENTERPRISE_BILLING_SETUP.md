# 🏢 Signet Protocol - Enterprise Billing Setup Guide

## Overview

This guide implements the enterprise billing structure outlined in the Signet Protocol product strategy, providing cryptographic auditability with usage-based billing that scales from startups to large enterprises.

## 🎯 Strategic Positioning

**"Auditability is the fulcrum. Cryptographic lineage (CIDs + signatures + verifiable receipts) is the enterprise unlock."**

The Signet Protocol billing system provides:
- **Verified Exchanges (VEx)**: Cryptographically verified AI interactions
- **Fallback Units (FU)**: Token-based billing for LLM repair services
- **Reserved Capacity**: Enterprise-grade commitments with overage tiers
- **Compliance Ready**: Audit trails for EU AI Act and NIST RMF requirements

## 📊 Billing Structure

### Core Metrics

| Metric | Description | Billing Unit | Enterprise Value |
|--------|-------------|--------------|------------------|
| **VEx** | Verified Exchange operations | Per successful exchange | Cryptographic proof of AI interactions |
| **FU** | Fallback Units (tokens) | Per token consumed | LLM repair when validation fails |

### Pricing Tiers

#### VEx (Verified Exchange) Pricing
- **Tier 1**: $0.005 per VEx (up to 50,000/month)
- **Tier 2**: $0.008 per VEx (50,000+/month)

#### FU (Fallback Units) Pricing  
- **Tier 1**: $0.001 per token (up to 250,000/month)
- **Tier 2**: $0.0008 per token (250,000+/month)

### Subscription Plans

| Plan | Monthly Fee | VEx Included | FU Tokens Included | Target Customer |
|------|-------------|--------------|-------------------|-----------------|
| **Starter** | $499 | 10,000 | 50,000 | Growing startups |
| **Professional** | $1,999 | 100,000 | 500,000 | Mid-market companies |
| **Enterprise** | $9,999 | 1,000,000 | 5,000,000 | Large enterprises |

## 🚀 Setup Instructions

### 1. Create Stripe Products

Run the setup script to create all necessary Stripe products and pricing:

```bash
# Set your Stripe API key
export STRIPE_SECRET_KEY=sk_live_your_key_here

# Create products and pricing (LIVE mode - creates real products)
python setup_stripe_products.py

# Or generate demo configuration first
python setup_stripe_products_demo.py
```

### 2. Configure Reserved Capacity

Update your `reserved.json` with the generated enterprise configuration:

```json
{
  "enterprise_customer": {
    "vex_reserved": 1000000,
    "fu_reserved": 5000000,
    "subscription_plan": "price_signet_enterprise_monthly_9999",
    "vex_overage_tiers": [
      {
        "threshold": 500000,
        "price_per_unit": 0.005,
        "stripe_item": "price_signet_vex_tier1_005"
      }
    ],
    "fu_overage_tiers": [
      {
        "threshold": 2500000,
        "price_per_unit": 0.001,
        "stripe_item": "price_signet_fu_tier1_001"
      }
    ]
  }
}
```

### 3. Configure API Keys

Set up tenant API keys with Stripe item mappings:

```json
{
  "enterprise_api_key_001": {
    "tenant": "enterprise_customer",
    "allowlist": ["*.enterprise.com", "api.partners.com"],
    "fallback_enabled": true,
    "fu_monthly_limit": 5000000,
    "stripe_item_vex": "price_signet_vex_tier1_005",
    "stripe_item_fu": "price_signet_fu_tier1_001"
  }
}
```

### 4. Environment Configuration

Update your `.env` file:

```bash
# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_your_key_here
SP_RESERVED_CONFIG=./reserved_enterprise.json

# Database (PostgreSQL recommended for production)
SP_STORAGE=postgres
SP_POSTGRES_URL=postgresql://user:pass@localhost/signet

# API Keys with Stripe Integration
SP_API_KEYS='{"enterprise_key":{"tenant":"enterprise_customer","stripe_item_vex":"price_signet_vex_tier1_005"}}'
```

## 💼 Enterprise Features

### Cryptographic Auditability

Every exchange generates:
- **Hash-linked receipts** with SHA-256 integrity
- **Ed25519 signatures** for non-repudiation
- **JCS canonicalization** for deterministic hashing
- **Exportable audit trails** for compliance

### Compliance Controls

| Requirement | Signet Control | Evidence |
|-------------|----------------|----------|
| **EU AI Act - Record Keeping** | Signed receipts + export bundles | `GET /v1/receipts/export/{trace_id}` |
| **NIST RMF - Governance** | Tenant configs + JWKS rotation | `/.well-known/jwks.json` |
| **SOX Compliance** | Immutable audit logs | Hash-linked receipt chains |
| **GDPR Data Protection** | Tenant isolation + access controls | Per-tenant API keys |

### Performance SLOs

- **p50 Latency**: ≤ 10ms added latency (no-fallback path)
- **p95 Latency**: ≤ 40ms added latency (no-fallback path)
- **Availability**: 99.9% uptime SLA
- **Throughput**: 10,000+ VEx/second per instance

## 📈 Monitoring & Metrics

### Key Metrics

```prometheus
# Business Metrics
signet_exchanges_total{tenant,api_key}
signet_reserved_capacity{tenant,type="vex|fu"}
signet_overage_charges_total{tenant,type,tier}

# Performance Metrics
signet_exchange_duration_seconds{phase="total|auth|transform|policy|receipt"}
signet_fallback_used_total{tenant}
signet_denied_total{reason,tenant}
```

### Billing Dashboard

Access comprehensive billing data:

```bash
curl -H "X-SIGNET-API-Key: your_key" \
  http://localhost:8088/v1/billing/dashboard
```

## 🎯 Go-to-Market Demos

### Finance Demo: ISO 20022 Invoice Processing

```bash
# Process invoice with cryptographic verification
curl -X POST http://localhost:8088/v1/exchange \
  -H "X-SIGNET-API-Key: finance_demo_key" \
  -H "Content-Type: application/json" \
  -d '{
    "payload_type": "openai.tooluse.invoice.v1",
    "target_type": "invoice.iso20022.v1",
    "payload": {
      "tool_calls": [{
        "function": {
          "name": "create_invoice",
          "arguments": "{\"invoice_id\":\"INV-001\",\"amount\":1000,\"currency\":\"USD\"}"
        }
      }]
    },
    "forward_url": "https://bank-api.example.com/invoices"
  }'
```

**Value Proposition**: "Auditor can verify invoice processing in 90 seconds with cryptographic proof."

### Healthcare Demo: HL7/FHIR Compliance

```bash
# Process patient data with PHI protection
curl -X POST http://localhost:8088/v1/exchange \
  -H "X-SIGNET-API-Key: healthcare_demo_key" \
  -d '{
    "payload_type": "hl7.fhir.patient.v1",
    "target_type": "hl7.fhir.anonymized.v1",
    "payload": {"patient_data": "..."},
    "semantic_invariants": ["no_phi_leakage", "minimum_necessary"]
  }'
```

**Value Proposition**: "Prove 'minimum necessary' compliance via cryptographic invariant checks."

### Supply Chain Demo: Provenance Tracking

```bash
# Link PO → ASN → Invoice with hash-linked receipts
curl -X POST http://localhost:8088/v1/exchange \
  -H "X-SIGNET-API-Key: supply_chain_key" \
  -d '{
    "payload_type": "supply.purchase_order.v1",
    "target_type": "supply.shipment_notice.v1",
    "payload": {"po_number": "PO-12345", "items": [...]}
  }'
```

**Value Proposition**: "Counterfeit detection with immutable provenance chain."

## 🔧 Payment Links

Direct subscription links for sales:

- **Starter Plan**: https://buy.stripe.com/signet-starter-plan
- **Professional Plan**: https://buy.stripe.com/signet-professional-plan  
- **Enterprise Plan**: https://buy.stripe.com/signet-enterprise-plan

## 📞 Enterprise Sales Process

### 1. Discovery Call
- Identify AI interaction volume
- Assess compliance requirements
- Determine integration complexity

### 2. Technical Demo
- Show vertical-specific use case
- Demonstrate cryptographic verification
- Prove latency performance (< 40ms p95)

### 3. Pilot Program
- 30-day trial with Starter Plan
- Technical integration support
- Success metrics tracking

### 4. Enterprise Contract
- Reserved capacity commitment
- Custom SLA terms
- Dedicated support

## 🛡️ Security & Compliance

### SSRF Protection
- DNS → public IP validation
- HTTPS-only forwarding
- 1MB response size limits
- No redirect following

### Audit Requirements
- 7-year data retention
- Immutable receipt chains
- Cryptographic signatures
- Export bundle generation

### Regulatory Mapping

#### EU AI Act (High-Risk Systems)
- ✅ **Record-keeping**: Hash-linked receipt chains
- ✅ **Traceability**: CID-based content tracking  
- ✅ **Robustness**: HEL policy enforcement
- ✅ **Post-market monitoring**: Prometheus metrics

#### NIST AI RMF
- ✅ **GOVERN**: Tenant isolation + JWKS rotation
- ✅ **MAP/MEASURE**: Schema validation + metrics
- ✅ **MANAGE**: Quotas + incident export

## 📊 Success Metrics

### Technical KPIs
- **VEx Success Rate**: > 97% without fallback
- **Fallback Rate**: < 3% and trending down
- **Latency Added**: ≤ 40ms (p95)
- **SDK Adoption**: ≥ 30% of tenants verifying in CI

### Business KPIs
- **Monthly Recurring Revenue**: Track subscription growth
- **Usage Growth**: VEx/FU consumption trends
- **Customer Expansion**: Tier upgrades over time
- **Compliance Wins**: Audit pass rates

## 🚀 Next Steps

1. **Review Configuration**: Validate generated Stripe products
2. **Create Real Products**: Run `python setup_stripe_products.py`
3. **Configure Environment**: Update `.env` with Stripe IDs
4. **Test Integration**: Verify billing flows
5. **Launch Sales**: Use payment links and demos
6. **Monitor Performance**: Track KPIs and SLOs

---

**The Signet Protocol: Enterprise-ready cryptographic verification with transparent, usage-based billing.** 🔐💼
