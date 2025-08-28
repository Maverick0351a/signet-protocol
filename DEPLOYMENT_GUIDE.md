# Signet Protocol - Production Deployment Guide

## 🎯 Current Status
✅ **52 tests passing, 1 skipped (current suite)**  
✅ **Server running and healthy on port 8088**  
✅ **All advanced features implemented and tested**  

## 🚀 Production Deployment Steps

### 1. Environment Setup

Copy the production environment template:
```bash
cp .env.production .env
```

Edit `.env` with your actual secrets:

#### Required Secrets:
- **OpenAI API Key**: Get from https://platform.openai.com/api-keys
- **Stripe API Key**: Get from https://dashboard.stripe.com/apikeys
- **Private Key**: Generate RSA key for receipt signing
- **Production API Keys**: Create secure API keys for your tenants

#### Generate Private Key:
```bash
# Generate RSA private key
openssl genrsa -out signet_private.pem 2048

# Convert to base64 for environment variable
base64 -w 0 signet_private.pem > signet_private_b64.txt
```

### 2. Database Setup

#### Option A: PostgreSQL (Recommended for Production)
```bash
# Install PostgreSQL
# Create database
createdb signet_production

# Update .env
SP_STORAGE=postgres
SP_POSTGRES_URL=postgresql://username:password@localhost:5432/signet_production
```

#### Option B: SQLite (Development/Small Scale)
```bash
# Create data directory
mkdir -p data

# Update .env
SP_STORAGE=sqlite
SP_DB_PATH=./data/signet_production.db
```

### 3. Reserved Capacity Configuration

Edit `reserved_production.json` with your customer tiers:
```json
{
  "your_customer_name": {
    "vex_reserved": 100000,
    "fu_reserved": 500000,
    "vex_overage_tiers": [
      {"threshold": 50000, "price_per_unit": 0.005, "stripe_item": "si_your_stripe_item"}
    ],
    "fu_overage_tiers": [
      {"threshold": 250000, "price_per_unit": 0.0008, "stripe_item": "si_your_fu_item"}
    ]
  }
}
```

### 4. Stripe Integration Setup

Create Stripe products and price items:
```bash
# Example Stripe CLI commands
stripe products create --name "Signet VEx Tier 1"
stripe prices create --product prod_xxx --unit-amount 500 --currency usd
```

### 5. API Key Configuration

Format for SP_API_KEYS in `.env`:
```json
{
  "your_secure_api_key_here": {
    "tenant": "your_company",
    "allowlist": ["your-webhook-domain.com", "api.trusted-partner.com"],
    "fallback_enabled": true,
    "fu_monthly_limit": 50000,
    "stripe_item_vex": "si_your_vex_item",
    "stripe_item_fu": "si_your_fu_item"
  }
}
```

### 6. Security Configuration

#### Allowlist Setup:
```bash
# Global allowlist for all tenants
SP_HEL_ALLOWLIST=api.openai.com,hooks.slack.com,your-trusted-domain.com
```

#### Network Security:
- Enable HTTPS in production
- Use reverse proxy (nginx/Apache)
- Configure firewall rules
- Enable rate limiting

### 7. Start Production Server

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests to verify
python -m pytest tests/ -v

# Start production server
uvicorn server.main:app --host 0.0.0.0 --port 8088 --workers 4
```

### 8. Health Checks

Verify deployment:
```bash
# Health check
curl http://your-domain:8088/healthz

# Metrics
curl http://your-domain:8088/metrics

# JWKS endpoint
curl http://your-domain:8088/.well-known/jwks.json
```

## 📊 Monitoring Setup

### Prometheus Metrics
The server exposes Prometheus metrics at `/metrics` (core pipeline, billing, latency, fallback):
- `signet_exchanges_total`
- `signet_denied_total`
- `signet_forward_total`
- `signet_reserved_capacity{tenant,type}`
- `signet_overage_charges_total{tenant,type,tier}`

### Log Monitoring
Monitor application logs for:
- Authentication failures
- Policy violations
- Fallback usage
- Billing events

## 🔒 Security Checklist

- [ ] Private key securely stored and base64 encoded
- [ ] API keys are cryptographically secure (32+ chars)
- [ ] Database credentials are secure
- [ ] HTTPS enabled with valid certificates
- [ ] Firewall configured (only port 8088 exposed)
- [ ] Regular security updates applied
- [ ] Monitoring and alerting configured

## 🎯 Production Features Active

### Security:
✅ IP Pinning & SSRF Protection  
✅ Response Size Limiting (1MB)  
✅ Input Validation & Sanitization  
✅ RFC 8785 JCS Canonicalization  

### Billing:
✅ Token-Level Metering  
✅ Reserved Capacity Management  
✅ Tiered Overage Pricing  
✅ Stripe Integration  

### Scalability:
✅ PostgreSQL Support  
✅ Connection Pooling  
✅ Prometheus Metrics  
✅ Multi-tenant Architecture  

### Reliability:
✅ Transaction Safety  
✅ Conflict Resolution  
✅ Comprehensive Error Handling  
✅ All tests green (52 passed, 1 skipped)  

## 🚀 Next Steps

1. **Fill in your actual secrets** in `.env`
2. **Configure your database** (PostgreSQL recommended)
3. **Set up Stripe products** and update reserved capacity config
4. **Deploy to your production environment**
5. **Configure monitoring and alerting**
6. **Test with real API calls**

## 📞 Support

The Signet Protocol is now production-ready with enterprise-grade features:
- Advanced security protections
- Flexible billing models
- Comprehensive monitoring
- Scalable architecture

All tests are passing (52 + 1 skipped), confirming the system is ready for production deployment!

## 🚀 Fly.io Deployment (Managed Runtime)

### 1. Prerequisites
```bash
fly auth login
fly apps create signet-protocol || true
```

### 2. Secrets (never commit secrets)
```bash
fly secrets set \
  SP_API_KEYS='{"demo_key":{"tenant":"acme","fallback_enabled":true}}' \
  SP_OPENAI_API_KEY=sk-openai-xxxxx \
  SP_STRIPE_API_KEY=sk-stripe-xxxxx \
  SP_PRIVATE_KEY_B64=$(base64 -w0 signet_private.pem) \
  SP_RESERVED_CONFIG=/app/reserved.json
```

### 3. Deploy
```bash
fly deploy
```

### 4. Verify
```bash
curl https://signet-protocol.fly.dev/healthz
curl https://signet-protocol.fly.dev/metrics | head
```

### 5. Scaling & Concurrency
SQLite is fine for low volume. For multi-instance horizontal scaling use PostgreSQL (managed DB) and set `SP_STORAGE=postgres` + `SP_POSTGRES_URL` secret.
```bash
fly scale count 1          # start with single instance (SQLite)
fly scale memory 512       # adjust memory
fly scale vm shared-cpu-1x # choose VM size
```

### 6. Persistent Storage (SQLite)
If you keep SQLite in production mount a volume:
```bash
fly volumes create signet_data --size 1
# Then add to fly.toml (example):
# [[mounts]]
#   source = "signet_data"
#   destination = "/app/data"
```

### 7. Observability
Expose metrics (already). For tracing set OTEL vars:
```bash
fly secrets set OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector.internal:4317" OTEL_SERVICE_NAME=signet
```

### 8. Rolling Updates
`fly deploy` performs rolling replacement; health checks (configured in `fly.toml`) gate traffic shift.

### 9. Post-Deploy Admin
Reload reserved capacity without restart:
```bash
curl -X POST -H "X-SIGNET-API-Key: demo_key" https://signet-protocol.fly.dev/v1/admin/reload-reserved
```

### 10. Next Hardening Steps
- Add rate limiting / WAF (Fly Machines + proxy or upstream CDN)
- Enable HTTPS redirects (handled automatically for 443; optionally force redirect in app/middleware)
- Move secrets rotation into scheduled workflow
- Add log aggregation (Fly logs -> Loki / Datadog)
