# Signet Protocol Deployment Guide

**Production-Ready Deployment Instructions**

This guide covers deploying the Signet Protocol server in production environments with enterprise-grade security, monitoring, and scalability.

## 🚀 Quick Production Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/Maverick0351a/signet-protocol
cd signet-protocol

# Configure environment
cp .env.example .env
# Edit .env with your production secrets

# Deploy with monitoring stack
docker-compose up -d

# Verify deployment
curl http://localhost:8088/healthz
```

### Option 2: Kubernetes

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=signet-protocol
```

## 🔧 Configuration

### Environment Variables

```bash
# Server Configuration
SIGNET_HOST=0.0.0.0
SIGNET_PORT=8088
SIGNET_DEBUG=false

# Database (Production)
DATABASE_URL=postgresql://user:pass@host:5432/signet
REDIS_URL=redis://redis:6379

# Cryptographic Keys
SIGNET_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# External Services
OPENAI_API_KEY=sk-...
STRIPE_API_KEY=sk_live_...

# Policy Configuration
SIGNET_ALLOWED_HOSTS=api.openai.com,api.anthropic.com,your-webhook.com

# Billing Configuration
SIGNET_ENABLE_BILLING=true
SIGNET_DEFAULT_VEX_LIMIT=10000
SIGNET_DEFAULT_FU_LIMIT=50000

# Security Configuration
SIGNET_MAX_PAYLOAD_SIZE=10000000
SIGNET_MAX_RESPONSE_SIZE=50000000
SIGNET_REQUEST_TIMEOUT=30

# Monitoring
SIGNET_ENABLE_METRICS=true
SIGNET_LOG_LEVEL=INFO
```

### Key Generation

```bash
# Generate Ed25519 private key
openssl genpkey -algorithm Ed25519 -out private_key.pem

# Extract public key
openssl pkey -in private_key.pem -pubout -out public_key.pem

# Convert to environment variable format
cat private_key.pem | tr '\n' '\\n'
```

## 🗄️ Database Setup

### PostgreSQL (Recommended)

```sql
-- Create database and user
CREATE DATABASE signet;
CREATE USER signet WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE signet TO signet;
```

### Connection Pooling

```bash
# Use connection pooling for production
DATABASE_URL=postgresql://user:pass@host:5432/signet?pool_size=20&max_overflow=30
```

## 🔒 Security Hardening

### TLS/SSL Configuration

```nginx
# Nginx reverse proxy configuration
server {
    listen 443 ssl http2;
    server_name signet.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 📊 Monitoring & Observability

### Prometheus Metrics

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'signet-protocol'
    static_configs:
      - targets: ['localhost:8088']
    metrics_path: '/metrics'
```

### Health Checks

```bash
#!/bin/bash
# health_check.sh
HEALTH_URL="http://localhost:8088/healthz"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "✓ Signet Protocol is healthy"
    exit 0
else
    echo "✗ Signet Protocol health check failed (HTTP $RESPONSE)"
    exit 1
fi
```

## 🔄 High Availability

### Load Balancer Configuration

```nginx
# nginx.conf
upstream signet_backend {
    server signet1:8088 max_fails=3 fail_timeout=30s;
    server signet2:8088 max_fails=3 fail_timeout=30s;
    server signet3:8088 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://signet_backend;
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }
}
```

## 🧪 Testing Production Deployment

### Smoke Tests

```bash
#!/bin/bash
# smoke_test.sh
BASE_URL="https://signet.yourdomain.com"
API_KEY="your-production-api-key"

# Health check
echo "Testing health endpoint..."
curl -f $BASE_URL/healthz || exit 1

# Metrics endpoint
echo "Testing metrics endpoint..."
curl -f $BASE_URL/metrics || exit 1

# JWKS endpoint
echo "Testing JWKS endpoint..."
curl -f $BASE_URL/.well-known/jwks.json || exit 1

echo "✓ All smoke tests passed"
```

## 🚨 Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   docker stats signet-protocol
   
   # Adjust container limits
   docker run --memory=2g --memory-swap=4g signet-protocol
   ```

2. **Database Connection Issues**
   ```bash
   # Check connection pool
   psql -c "SELECT * FROM pg_stat_activity WHERE datname='signet';"
   ```

3. **Certificate Issues**
   ```bash
   # Check certificate expiry
   openssl x509 -in cert.pem -text -noout | grep "Not After"
   ```

## 📞 Support

For production support:
- **Documentation**: [GitHub Repository](https://github.com/Maverick0351a/signet-protocol)
- **Issues**: [GitHub Issues](https://github.com/Maverick0351a/signet-protocol/issues)
- **Security**: Report security issues privately

---

**Ready for Enterprise Deployment** 🚀