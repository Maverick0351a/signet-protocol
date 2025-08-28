# Signet Protocol Integrations - Publishing Guide

This guide covers how to publish all the Signet Protocol integrations to their respective platforms.

## 📦 Ready for Publishing

### 1. Airflow Provider (PyPI)

**Status**: ✅ Package built and ready
**Location**: `dist/signet_airflow_provider-1.0.0*`

```bash
# Install dependencies
pip install twine build

# Build package (already done)
cd integrations/airflow
python setup.py sdist bdist_wheel

# Upload to TestPyPI (for testing)
python -m twine upload --repository testpypi dist/*

# Upload to PyPI (production)
python -m twine upload dist/*
```

**Installation after publishing**:
```bash
pip install signet-airflow-provider
```

### 2. VS Code Extension (VS Code Marketplace)

**Status**: ✅ Extension ready for packaging
**Location**: `vscode-extension/`

```bash
# Install dependencies
cd vscode-extension
npm install

# Install vsce (VS Code Extension CLI)
npm install -g vsce

# Package extension
vsce package

# Publish to marketplace (requires publisher account)
vsce publish
```

**Installation after publishing**:
- Search "Signet Lens" in VS Code Extensions
- Or: `code --install-extension signet-lens`

### 3. JavaScript SDK (NPM)

**Status**: ✅ Ready for NPM publishing
**Location**: `sdk/javascript/`

```bash
cd sdk/javascript

# Build the package
npm run build

# Publish to NPM
npm publish

# Or publish to NPM with scoped package
npm publish --access public
```

**Installation after publishing**:
```bash
npm install signet-protocol
```

### 4. Python SDK (PyPI)

**Status**: ✅ Package built and ready
**Location**: `dist/signet_verify-1.0.0*`

```bash
cd sdk/python

# Build package
python setup.py sdist bdist_wheel

# Upload to PyPI
python -m twine upload dist/*
```

**Installation after publishing**:
```bash
pip install signet-verify
```

## 🔄 Integration Submissions

### 5. Prefect Hub

**Status**: ✅ Ready for submission
**Location**: `integrations/prefect/`

**Steps**:
1. Fork the [Prefect Collections repository](https://github.com/PrefectHQ/prefect-collection-template)
2. Submit PR with the SignetExchange block
3. Follow Prefect Hub submission guidelines

### 6. Zapier Platform (Private Beta)

**Status**: ✅ Ready for private beta
**Location**: `integrations/zapier/`

**Steps**:
1. Create Zapier Developer Account
2. Upload the integration package
3. Submit for private beta review
4. Configure triggers and actions

### 7. n8n Community Nodes

**Status**: ✅ Ready for submission
**Location**: `integrations/n8n/`

**Steps**:
1. Fork [n8n-nodes-starter](https://github.com/n8n-io/n8n-nodes-starter)
2. Add SignetProtocol node
3. Submit to n8n community repository
4. Follow n8n node development guidelines

## 📊 Monitoring & SIEM Deployments

### 8. Datadog Integration

**Status**: ✅ Ready for deployment
**Location**: `integrations/datadog/`

**Deployment**:
```bash
# Install Datadog agent with custom integration
pip install datadog
python integrations/datadog/signet_datadog.py

# Configure dashboards and alerts in Datadog UI
```

### 9. Splunk Configuration

**Status**: ✅ Ready for deployment
**Location**: `integrations/splunk/`

**Deployment**:
1. Copy `signet_splunk_config.conf` to Splunk configuration directory
2. Restart Splunk services
3. Configure index mappings and saved searches

### 10. ELK Stack Pipeline

**Status**: ✅ Ready for deployment
**Location**: `integrations/elk/`

**Deployment**:
```bash
# Deploy Logstash pipeline
cp integrations/elk/logstash/signet-pipeline.conf /etc/logstash/conf.d/

# Restart Logstash
sudo systemctl restart logstash

# Configure Kibana dashboards
```

## 🛠️ Development Tools

### 11. Enhanced CLI Tools

**Status**: ✅ Ready for use
**Location**: `tools/signet_cli.py`

**Usage**:
```bash
# Test mapping transformations
python tools/signet_cli.py map test --mapping mapping.json --sample data.json

# Validate policy configuration
python tools/signet_cli.py policy lint --allowlist "api.example.com" --check-dns

# Schema validation
python tools/signet_cli.py schema validate --input-schema input.json --data sample.json
```

## 📚 API Documentation

### 12. OpenAPI Specification

**Status**: ✅ Ready for hosting
**Location**: `openapi.yaml`

**Deployment Options**:

1. **GitHub Pages**:
   ```bash
   # Host on GitHub Pages with ReDoc
   # Copy openapi.yaml to docs/ folder
   # Enable GitHub Pages in repository settings
   ```

2. **Swagger Hub**:
   - Upload `openapi.yaml` to SwaggerHub
   - Generate client SDKs automatically

3. **Self-hosted ReDoc**:
   ```bash
   # Serve with ReDoc
   npx redoc-cli serve openapi.yaml
   ```

## 🔐 Authentication & Setup

### Required Accounts & Tokens

1. **PyPI Account**: For Python packages
   - Create account at https://pypi.org
   - Generate API token
   - Configure `~/.pypirc`

2. **NPM Account**: For JavaScript packages
   - Create account at https://npmjs.com
   - Login: `npm login`

3. **VS Code Publisher**: For VS Code extensions
   - Create publisher account
   - Generate Personal Access Token
   - Configure vsce: `vsce login <publisher>`

4. **Zapier Developer**: For Zapier integration
   - Apply for developer account
   - Create private app

5. **Datadog Account**: For monitoring integration
   - API key and application key required

## 📋 Publishing Checklist

### Pre-Publishing
- [ ] All packages built successfully
- [ ] Tests passing
- [ ] Documentation complete
- [ ] Version numbers updated
- [ ] Changelog updated
- [ ] License files included

### Publishing Order
1. [ ] Python SDK to PyPI
2. [ ] JavaScript SDK to NPM
3. [ ] Airflow Provider to PyPI
4. [ ] VS Code Extension to Marketplace
5. [ ] Submit Prefect block to Hub
6. [ ] Submit Zapier integration for review
7. [ ] Submit n8n node to community
8. [ ] Deploy monitoring integrations
9. [ ] Host API documentation

### Post-Publishing
- [ ] Update installation instructions
- [ ] Announce releases
- [ ] Monitor for issues
- [ ] Gather user feedback
- [ ] Plan next iteration

## 🚀 Automated Publishing (CI/CD)

### GitHub Actions Workflow

Create `.github/workflows/publish.yml`:

```yaml
name: Publish Packages

on:
  release:
    types: [published]

jobs:
  publish-python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Build and publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          pip install build twine
          python -m build
          twine upload dist/*

  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'
      - name: Publish to NPM
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          cd sdk/javascript
          npm ci
          npm run build
          npm publish

  publish-vscode:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Publish VS Code Extension
        env:
          VSCE_PAT: ${{ secrets.VSCE_PAT }}
        run: |
          cd vscode-extension
          npm ci
          npm install -g vsce
          vsce publish
```

## 📞 Support & Maintenance

### Community Support
- GitHub Issues for bug reports
- Discussions for questions
- Documentation wiki

### Enterprise Support
- Priority support channels
- Custom integration assistance
- SLA agreements

---

## 🎯 Next Steps

1. **Immediate**: Publish core SDKs (Python, JavaScript)
2. **Week 1**: Publish Airflow provider and VS Code extension
3. **Week 2**: Submit integrations to respective platforms
4. **Week 3**: Deploy monitoring integrations
5. **Month 1**: Gather feedback and iterate

All integrations are production-ready and include comprehensive error handling, monitoring, and documentation. The ecosystem provides complete coverage for orchestration, automation, development, and monitoring workflows.
