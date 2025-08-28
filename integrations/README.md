# Signet Protocol Integrations

This directory contains integrations and tools for working with Signet Protocol across different platforms and workflows.

## 📦 Available Integrations

### Postman Collection
- **Core API Collection**: `postman/Signet-Protocol-Collection.json`
- **Receipt Verification Flow**: `postman/Signet-Receipt-Verification.postman_collection.json`
- **Environment**: `postman/Signet-Protocol-Environment.json`
- **Features**:
  - Complete API testing suite
  - Automated test scripts
  - Multi-hop chain testing
  - Error scenario validation
  - Receipt verification & linkage integrity tests (bundle export)

### GitHub Actions
- **Action**: `.github/actions/signet-verify/`
- **Example Workflow**: `.github/workflows/signet-verify-example.yml`
- **Features**:
  - CI/CD receipt verification
  - Test vector validation
  - Server health checks
  - Automated PR comments

### Framework Adapters
- **LangChain**: `../adapters/langchain/signet_callback.py`
- **LlamaIndex**: Coming soon
- **CrewAI**: Coming soon
- **AutoGen**: Coming soon

## 🚀 Quick Start

### Postman Setup

1. **Import Collection**:
   ```bash
   # Import the collection file into Postman
   File → Import → integrations/postman/Signet-Protocol-Collection.json
   ```

2. **Import Environment**:
   ```bash
   # Import the environment file
   File → Import → integrations/postman/Signet-Protocol-Environment.json
   ```

3. **Configure Variables**:
   - `SIGNET_BASE_URL`: Your Signet Protocol server URL
   - `SIGNET_API_KEY`: Your API key
   - `FORWARD_URL`: Webhook URL for forwarded exchanges

4. **Run Tests**:
   - Individual requests for manual testing
   - Collection runner for automated testing
   - Monitor for continuous validation

### GitHub Actions Setup

1. **Add to Workflow**:
   ```yaml
   - name: Verify Signet Protocol
     uses: ./.github/actions/signet-verify
     with:
       test-vectors-path: 'test-vectors'
       jwks-url: 'https://your-server/.well-known/jwks.json'
       fail-on-error: 'true'
   ```

2. **Configure Secrets**:
   - `SIGNET_API_KEY`: Your API key (if needed)
   - `SIGNET_SERVER_URL`: Your server URL (if needed)

## 📋 Test Scenarios

### Basic Exchange Flow
1. **Create Exchange** → Verify receipt generation
2. **Get Chain** → Validate receipt chain integrity
3. **Export Bundle** → Test signed export functionality

### Multi-hop Chain Testing
1. **First Exchange** → Create genesis receipt
2. **Second Exchange** → Extend chain with linked receipt
3. **Chain Validation** → Verify complete chain integrity

### Error Handling
1. **Invalid API Key** → Test authentication
2. **Malformed Payload** → Test input validation
3. **Missing Headers** → Test required headers

## 🔧 Configuration

### Postman Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SIGNET_BASE_URL` | Server base URL | `http://localhost:8088` |
| `SIGNET_API_KEY` | Authentication key | `demo_key` |
| `FORWARD_URL` | Webhook endpoint | `https://webhook.site/...` |
| `TRACE_ID` | Current trace ID | Auto-generated |

### Environment-Specific Settings

#### Development
```json
{
  "SIGNET_BASE_URL": "http://localhost:8088",
  "SIGNET_API_KEY": "demo_key",
  "FORWARD_URL": "https://postman-echo.com/post"
}
```

#### Staging
```json
{
  "SIGNET_BASE_URL": "https://staging-signet.example.com",
  "SIGNET_API_KEY": "staging_key_here",
  "FORWARD_URL": "https://staging-webhook.example.com"
}
```

#### Production
```json
{
  "SIGNET_BASE_URL": "https://signet.example.com",
  "SIGNET_API_KEY": "{{PRODUCTION_API_KEY}}",
  "FORWARD_URL": "https://webhook.example.com"
}
```

## 📊 Monitoring & Validation

### Automated Tests
The Postman collection includes automated tests that verify:

- ✅ Response structure validation
- ✅ Receipt hash verification
- ✅ Chain linkage integrity
- ✅ Timestamp format validation
- ✅ Error response handling
 - ✅ Receipt linkage chain prev_receipt_hash integrity (verification flow collection)

### CI/CD Integration
The GitHub Action provides:

- 🔍 Test vector verification
- 🏥 Server health monitoring
- 📈 Performance tracking
- 🚨 Failure notifications

## 🛠️ Advanced Usage

### Custom Test Vectors
Create your own test vectors in the `test-vectors/` directory:

```json
{
  "trace_id": "custom-test-001",
  "hop": 1,
  "ts": "2025-01-27T12:00:00Z",
  "cid": "sha256:...",
  "canon": "{...}",
  "algo": "sha256",
  "prev_receipt_hash": null,
  "policy": {"engine": "HEL", "allowed": true},
  "tenant": "test",
  "receipt_hash": "sha256:..."
}
```

### Custom Workflows
Extend the GitHub Action for your specific needs:

```yaml
- name: Custom Signet Verification
  uses: ./.github/actions/signet-verify
  with:
    test-vectors-path: 'custom-vectors'
    server-url: 'https://your-server.com'
    fail-on-error: 'false'  # Continue on failures
```

### Webhook Integration
### OpenTelemetry Collector

An OpenTelemetry Collector configuration is provided at `monitoring/otel-collector-config.yaml` and wired into `docker-compose.yml` via the `otel-collector` service. Spans are exported with the OTLP HTTP endpoint (`4318`) and currently logged locally. To forward to a backend (Tempo, Honeycomb, Lightstep, etc.) uncomment and configure an OTLP exporter in the collector config.

Service container sets `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces` enabling tracing automatically (see `server/utils/tracing.py`).

To add Jaeger UI, uncomment the `jaeger` service block in `docker-compose.yml` and browse to `http://localhost:16686`.

### Prometheus Recording & Alerts

Recording rules & alerts are defined in `monitoring/rules/signet_rules.yml` and loaded via `monitoring/prometheus.yml`. They provide precomputed p95/p99 quantiles and trigger alerts on:
- High p99 total latency (>2s for 5m)
- Elevated denied rate (>5/min for 10m)
- Fallback usage spike (>50 in 5m)

Regenerate metrics docs after metric changes:
```powershell
python scripts/generate_metrics_doc.py > docs/METRICS.md
```

Set up webhooks to receive forwarded exchanges:

```javascript
// Express.js webhook handler
app.post('/signet-webhook', (req, res) => {
  const { normalized, receipt, trace_id } = req.body;
  
  // Process verified exchange
  console.log(`Received verified exchange: ${trace_id}`);
  console.log(`Receipt hash: ${receipt.receipt_hash}`);
  
  res.status(200).json({ received: true });
});
```

## 🔗 Related Documentation

- [SR-1 Receipt Specification](../docs/SR-1-SIGNET-RECEIPT-SPEC.md)
- [SVX-1 Exchange Specification](../docs/SVX-1-VERIFIED-EXCHANGE-SPEC.md)
- [Python SDK Documentation](../sdk/python/README.md)
- [JavaScript SDK Documentation](../sdk/javascript/README.md)

## 🤝 Contributing

To add new integrations:

1. Create a new directory under `integrations/`
2. Include comprehensive documentation
3. Provide example configurations
4. Add automated tests where possible
5. Update this README with integration details

## 📞 Support

For integration support:
- Check the [main documentation](../README.md)
- Review [test examples](../tests/)
- Open an issue for specific integration problems
