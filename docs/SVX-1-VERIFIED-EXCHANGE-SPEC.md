# SVX-1: Verified Exchange Specification v1.0

## Abstract

The Verified Exchange (SVX-1) specification defines the precise semantics for counting, billing, and auditing successful AI-to-AI communication exchanges in the Signet Protocol ecosystem.

## 1. Overview

A Verified Exchange (VEx) represents a single, successful, end-to-end processing of an AI agent communication that:
- Passes input validation
- Completes transformation successfully  
- Satisfies policy requirements
- Generates a cryptographically signed receipt

VEx counting provides the foundation for usage-based billing, SLA monitoring, and compliance auditing.

## 2. VEx Counting Rules

### 2.1 VEx Increment Conditions

A VEx counter MUST increment by exactly 1 when ALL of the following conditions are met:

1. **Valid Authentication**: Request includes valid API key
2. **Schema Validation**: Input payload validates against declared schema
3. **Successful Transformation**: Payload transformation completes without errors
4. **Policy Compliance**: HEL policy evaluation returns `allowed: true`
5. **Receipt Generation**: Cryptographic receipt is successfully created and stored

### 2.2 VEx Non-Increment Conditions

A VEx counter MUST NOT increment when ANY of the following occurs:

```
HTTP 400: Malformed request, missing headers, invalid JSON
HTTP 401: Invalid or missing API key
HTTP 403: Policy denied (HEL allowlist violation, SSRF protection)
HTTP 409: Chain conflict (concurrent modification)
HTTP 422: Schema validation failure, transformation error
HTTP 429: Quota exceeded (FU limits, rate limits)
HTTP 500: Internal server error, storage failure
```

### 2.3 Idempotency Handling

- **First Request**: VEx increments, receipt created
- **Duplicate Request**: VEx does NOT increment, cached response returned
- **Response Header**: `X-Signet-Idempotency-Hit: 1` indicates cached response

## 3. Fallback Unit (FU) Semantics

### 3.1 FU Definition

Fallback Units (FU) measure AI service consumption when LLM-based JSON repair is used:
- 1 FU = 1 token consumed from OpenAI API (or equivalent)
- FU consumption is independent of VEx counting
- FU tokens are metered separately for precise billing

### 3.2 FU Counting Rules

```python
# FU tokens are counted when:
if fallback_repair_attempted and repair_successful:
    fu_tokens = openai_response.usage.total_tokens
    # Bill tenant for FU consumption
    bill_fallback_units(tenant, fu_tokens)
    
# FU tokens are NOT counted when:
# - Fallback is disabled for tenant
# - Repair attempt fails (API error, timeout)
# - No repair needed (JSON already valid)
```

### 3.3 FU Quota Enforcement

```python
def check_fu_quota(tenant_config, estimated_tokens):
    if not tenant_config.fallback_enabled:
        return False, "FALLBACK_DISABLED"
    
    monthly_limit = tenant_config.fu_monthly_limit
    if monthly_limit is None:
        return True, "ok"  # No limit
    
    current_usage = get_monthly_fu_usage(tenant_config.tenant)
    if current_usage + estimated_tokens > monthly_limit:
        return False, f"FU_QUOTA_EXCEEDED: {current_usage + estimated_tokens}/{monthly_limit}"
    
    return True, "ok"
```

## 4. Exchange States

### 4.1 State Diagram

```
[Request] → [Auth] → [Validate] → [Transform] → [Policy] → [Receipt] → [Success]
     ↓         ↓         ↓           ↓          ↓         ↓
   [401]    [422]    [422]       [403]      [500]    [200]
```

### 4.2 State Definitions

| State | HTTP Code | VEx Count | Description |
|-------|-----------|-----------|-------------|
| `AUTH_FAILED` | 401 | ❌ No | Invalid API key |
| `VALIDATION_FAILED` | 422 | ❌ No | Schema validation error |
| `TRANSFORM_FAILED` | 422 | ❌ No | JSON repair/transform error |
| `POLICY_DENIED` | 403 | ❌ No | HEL allowlist violation |
| `STORAGE_FAILED` | 500 | ❌ No | Receipt storage error |
| `SUCCESS` | 200 | ✅ Yes | Complete successful exchange |

### 4.3 Partial Success Handling

```python
# Scenario: Transform succeeds, but forwarding fails
if transform_success and policy_allowed:
    # VEx DOES count - core exchange completed
    vex_count += 1
    create_receipt(success=True)
    
    if forward_url and forward_failed:
        # Include forward failure in receipt
        receipt["forwarded"] = {
            "url": forward_url,
            "status_code": 0,
            "error": "Connection timeout"
        }
    
    return 200, response_with_receipt
```

## 5. Billing Integration

### 5.1 VEx Billing Events

```python
# Successful exchange
billing_buffer.enqueue_vex(
    api_key=api_key,
    stripe_item=tenant_config.stripe_item_vex,
    units=1,  # Always 1 per successful exchange
    tenant=tenant_config.tenant
)
```

### 5.2 FU Billing Events

```python
# Fallback usage
if fu_tokens_used > 0:
    billing_buffer.enqueue_fu(
        api_key=api_key,
        stripe_item=tenant_config.stripe_item_fu,
        units=fu_tokens_used,
        tenant=tenant_config.tenant
    )
```

### 5.3 Reserved Capacity Model

```json
{
  "tenant": "enterprise_customer",
  "vex_reserved": 100000,     // Pre-paid VEx allowance
  "fu_reserved": 500000,      // Pre-paid FU allowance
  "vex_overage_tiers": [
    {
      "threshold": 50000,     // Additional VEx beyond reserved
      "price_per_unit": 0.005, // Price per VEx in this tier
      "stripe_item": "si_vex_tier1"
    }
  ],
  "fu_overage_tiers": [
    {
      "threshold": 250000,    // Additional FU beyond reserved
      "price_per_unit": 0.0008, // Price per FU token
      "stripe_item": "si_fu_tier1"
    }
  ]
}
```

## 6. Monitoring & Metrics

### 6.1 Core Metrics

```prometheus
# VEx counting
signet_exchanges_total{tenant,api_key}

# FU consumption  
signet_fallback_used_total{tenant}
signet_fu_tokens_total{tenant}

# Policy enforcement
signet_denied_total{reason,tenant}

# Reserved capacity tracking
signet_reserved_capacity{tenant,type="vex|fu"}
signet_overage_charges_total{tenant,type,tier}
```

### 6.2 SLA Monitoring

```python
# Exchange success rate
success_rate = signet_exchanges_total / (signet_exchanges_total + signet_denied_total)

# Latency tracking
signet_exchange_duration_seconds{phase="total|auth|transform|policy|receipt"}

# Availability
signet_uptime_seconds
```

## 7. Audit Trail Requirements

### 7.1 Exchange Logging

Every exchange attempt MUST log:
```json
{
  "timestamp": "2025-01-27T12:00:00Z",
  "trace_id": "abc-123",
  "api_key_hash": "sha256:...",
  "tenant": "customer_a",
  "result": "SUCCESS|DENIED|ERROR",
  "vex_counted": true,
  "fu_tokens": 0,
  "policy_reason": "ok",
  "latency_ms": 45
}
```

### 7.2 Billing Reconciliation

Monthly billing reports MUST include:
- Total VEx consumed vs reserved capacity
- Total FU tokens consumed vs reserved capacity
- Overage charges by tier
- Failed exchange counts (not billed)

## 8. Security Considerations

### 8.1 Double-Counting Prevention

- Idempotency keys MUST prevent duplicate VEx counting
- Database constraints MUST prevent concurrent receipt creation
- Audit logs MUST be tamper-evident

### 8.2 Quota Bypass Prevention

- FU quota checks MUST occur before API calls
- VEx limits MUST be enforced at the database level
- Rate limiting MUST be independent of VEx/FU quotas

## 9. Implementation Guidelines

### 9.1 Database Schema

```sql
CREATE TABLE exchanges (
    trace_id VARCHAR(255) NOT NULL,
    hop INTEGER NOT NULL,
    api_key_hash VARCHAR(64) NOT NULL,
    tenant VARCHAR(255) NOT NULL,
    vex_counted BOOLEAN NOT NULL DEFAULT FALSE,
    fu_tokens INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    PRIMARY KEY (trace_id, hop)
);

CREATE INDEX idx_exchanges_tenant_month ON exchanges (tenant, DATE_TRUNC('month', created_at));
```

### 9.2 Atomic Operations

```python
def record_exchange(trace_id, hop, tenant, vex_counted, fu_tokens):
    with database.transaction():
        # Insert exchange record
        insert_exchange(trace_id, hop, tenant, vex_counted, fu_tokens)
        
        # Update monthly usage counters
        update_monthly_usage(tenant, vex_counted, fu_tokens)
        
        # Enqueue billing events
        if vex_counted:
            enqueue_vex_billing(tenant, 1)
        if fu_tokens > 0:
            enqueue_fu_billing(tenant, fu_tokens)
```

## 10. Compliance & Standards

### 10.1 Financial Accuracy

- VEx counting MUST be deterministic and auditable
- Billing events MUST be idempotent
- Usage reports MUST be cryptographically signed

### 10.2 Data Retention

- Exchange records MUST be retained for minimum 7 years
- Audit logs MUST be immutable and timestamped
- Receipt chains MUST be exportable for compliance

---

**Status**: Draft Specification  
**Version**: 1.0  
**Date**: 2025-01-27  
**Authors**: Signet Protocol Contributors
