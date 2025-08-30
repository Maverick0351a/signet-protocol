# Signet Protocol Repository Reorganization Plan

**Generated:** 2025-01-29  
**Branch:** chore/repo-hygiene-and-reorg  
**Status:** DRAFT - Awaiting Approval  

## Overview

This plan outlines a non-breaking reorganization of the Signet Protocol repository from the current flat structure to a clean monorepo layout with proper workspace boundaries, while preserving all Git history through `git mv` operations.

## Current Structure (BEFORE)

```
signet-protocol/
├── server/                    # FastAPI backend
├── sdk/                       # Multi-language SDKs
│   ├── javascript/
│   ├── python/
│   ├── wasm/
│   └── node/
├── vscode-extension/          # VS Code Signet Lens
├── vscode-extensions/         # Additional extensions
│   └── signet-chat-lens/
├── integrations/              # Third-party integrations
├── adapters/                  # Framework adapters
├── docs/                      # Documentation
├── tests/                     # Tests
├── examples/                  # Usage examples
├── tools/                     # CLI utilities
├── monitoring/                # Observability
├── .github/                   # CI/CD
└── [various config files]
```

## Target Structure (AFTER)

```
signet-protocol/
├── apps/
│   ├── core-api/              # FastAPI backend (moved from server/)
│   ├── console/               # Next.js Signet Console (future)
│   └── marketing/             # signetprotocol.com site (future)
├── extensions/
│   └── vscode-signet-lens/    # Unified VS Code extensions
├── packages/
│   ├── ui/                    # Shared React UI kit (future)
│   ├── sdk-js/                # JS verification SDK (from sdk/javascript/)
│   └── config/                # Shared configs (eslint/tailwind/turbo)
├── sdk/
│   └── python/                # Python verification SDK (from sdk/python/)
├── docs/                      # Specifications & compliance docs
├── examples/                  # Usage examples (preserved)
├── tools/                     # CLI utilities (preserved)
├── integrations/              # Third-party integrations (preserved)
├── adapters/                  # Framework adapters (preserved)
├── monitoring/                # Observability configs (preserved)
├── test-vectors/              # Test data (preserved)
├── .github/                   # CI/CD (updated paths)
└── [workspace configs]        # package.json, pnpm-workspace.yaml, turbo.json
```

## Move Map - Exact Git Commands

### Phase 1: Core Application Moves
```bash
# Create target directories
mkdir -p apps/core-api
mkdir -p extensions/vscode-signet-lens
mkdir -p packages/sdk-js
mkdir -p packages/config

# Move FastAPI backend
git mv server apps/core-api

# Consolidate VS Code extensions
git mv vscode-extension extensions/vscode-signet-lens/signet-lens
git mv vscode-extensions/signet-chat-lens extensions/vscode-signet-lens/signet-chat-lens

# Move JavaScript SDK to packages
git mv sdk/javascript packages/sdk-js

# Move Python SDK to sdk (keep existing structure)
git mv sdk/python sdk/python-temp
git mv sdk/wasm sdk/wasm-temp  
git mv sdk/node sdk/node-temp
rm -rf sdk/
mkdir sdk/
git mv sdk/python-temp sdk/python
# Note: wasm and node SDKs to be relocated in future phases
```

### Phase 2: WASM and Node SDK Placement (Future)
```bash
# These moves are deferred pending further analysis
# git mv sdk/wasm-temp packages/sdk-wasm
# git mv sdk/node-temp packages/sdk-node
```

### Phase 3: Clean Up Empty Directories
```bash
# Remove empty vscode-extensions directory
rmdir vscode-extensions
```

## Import/Alias Updates Required

### 1. Python Import Updates (apps/core-api/)

**File:** `apps/core-api/main.py`
```python
# Update any relative imports if needed
# Most imports should remain unchanged as they're relative within the moved directory
```

**File:** `pyproject.toml` (root)
```toml
# Update any path references to server/
# Change server/ references to apps/core-api/
```

### 2. TypeScript Path Updates

**File:** `packages/sdk-js/tsconfig.json`
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@signet/types": ["./src/types"],
      "@signet/core": ["./src/index"]
    }
  }
}
```

**File:** Root `tsconfig.json` (new)
```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@signet/sdk-js": ["./packages/sdk-js/src"],
      "@signet/ui": ["./packages/ui/src"],
      "@signet/config": ["./packages/config/src"]
    }
  },
  "references": [
    {"path": "./packages/sdk-js"},
    {"path": "./extensions/vscode-signet-lens/signet-lens"},
    {"path": "./extensions/vscode-signet-lens/signet-chat-lens"}
  ]
}
```

### 3. VS Code Extension Updates

**File:** `extensions/vscode-signet-lens/signet-lens/package.json`
```json
{
  "main": "./out/extension.js",
  "scripts": {
    "compile": "tsc -p ./",
    "build": "npm run compile"
  }
}
```

## Workspace Configuration

### 1. Root package.json
```json
{
  "name": "signet-protocol",
  "version": "1.0.0",
  "private": true,
  "workspaces": [
    "apps/*",
    "packages/*",
    "extensions/vscode-signet-lens/*"
  ],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint",
    "clean": "turbo run clean"
  },
  "devDependencies": {
    "turbo": "^1.10.0",
    "@types/node": "^18.0.0",
    "typescript": "^4.9.0"
  }
}
```

### 2. pnpm-workspace.yaml
```yaml
packages:
  - 'apps/*'
  - 'packages/*'
  - 'extensions/vscode-signet-lens/*'
```

### 3. turbo.json
```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", "out/**", "build/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"]
    },
    "lint": {
      "outputs": []
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "clean": {
      "cache": false
    }
  }
}
```

## CI/CD Updates Required

### 1. GitHub Actions Path Updates

**Files to Update:**
- `.github/workflows/signet-ci.yml`
- `.github/workflows/extension-ci.yml`
- `.github/workflows/publish_extension.yml`
- `.github/workflows/publish_python_client.yml`

**Example Changes:**
```yaml
# Before
- name: Test Python
  run: |
    cd server
    pytest tests/

# After  
- name: Test Python
  run: |
    cd apps/core-api
    pytest ../../tests/
```

### 2. Docker Updates

**File:** `Dockerfile`
```dockerfile
# Update COPY paths
COPY apps/core-api/ /app/
COPY requirements.txt /app/
COPY pyproject.toml /app/
```

### 3. Documentation Updates

**Files to Update:**
- `README.md` - Update repository layout section
- `DEVELOPERS.md` - Update development setup instructions
- `DEPLOYMENT_GUIDE.md` - Update deployment paths

## Package-Specific Configurations

### 1. apps/core-api/README.md
```markdown
# Signet Protocol Core API

FastAPI backend for the Signet Protocol.

## Development

```bash
# From repository root
cd apps/core-api
uvicorn main:app --reload --port 8088
```

## Testing

```bash
# From repository root
pytest tests/
```
```

### 2. packages/sdk-js/package.json
```json
{
  "name": "@signet/sdk-js",
  "version": "1.0.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "rollup -c",
    "test": "jest",
    "lint": "eslint src/"
  }
}
```

### 3. extensions/vscode-signet-lens/signet-lens/package.json
```json
{
  "name": "signet-lens",
  "displayName": "Signet Lens",
  "main": "./out/extension.js",
  "scripts": {
    "compile": "tsc -p ./",
    "package": "vsce package"
  }
}
```

## Risk Assessment & Mitigation

### High Risk Items
1. **Python Import Paths** - Risk: Breaking server functionality
   - **Mitigation:** Thorough testing of all import paths after move
   - **Rollback:** `git mv apps/core-api server`

2. **VS Code Extension Paths** - Risk: Extension build failures
   - **Mitigation:** Update all package.json and tsconfig.json files
   - **Rollback:** Restore original vscode-extension/ structure

3. **CI/CD Pipeline Failures** - Risk: Broken deployments
   - **Mitigation:** Update all workflow files before testing
   - **Rollback:** Revert workflow changes and directory moves

### Medium Risk Items
1. **Workspace Dependencies** - Risk: Package resolution issues
   - **Mitigation:** Gradual workspace adoption, test each package
   - **Rollback:** Remove workspace configs, restore flat structure

2. **Documentation Drift** - Risk: Outdated setup instructions
   - **Mitigation:** Update all documentation in same PR
   - **Rollback:** Revert documentation changes

### Low Risk Items
1. **Asset References** - Risk: Broken image/asset links
   - **Mitigation:** Verify asset paths in documentation
   - **Rollback:** Update asset references

## Rollback Plan

### Emergency Rollback (if critical issues found)
```bash
# 1. Revert all git mv operations
git mv apps/core-api server
git mv extensions/vscode-signet-lens/signet-lens vscode-extension
git mv extensions/vscode-signet-lens/signet-chat-lens vscode-extensions/signet-chat-lens
git mv packages/sdk-js sdk/javascript

# 2. Remove workspace configs
rm package.json pnpm-workspace.yaml turbo.json

# 3. Revert CI/CD changes
git checkout HEAD~1 -- .github/workflows/

# 4. Commit rollback
git add .
git commit -m "rollback: revert repository reorganization"
```

### Partial Rollback (if specific components fail)
- Individual `git mv` operations can be reversed
- Workspace configs can be removed independently
- CI/CD changes can be reverted per-file

## Validation Checklist

### Pre-Move Validation
- [ ] All tests pass in current structure
- [ ] CI/CD pipelines are green
- [ ] No uncommitted changes

### Post-Move Validation
- [ ] Python backend starts successfully: `cd apps/core-api && uvicorn main:app --port 8088`
- [ ] All Python tests pass: `pytest tests/`
- [ ] VS Code extensions build: `cd extensions/vscode-signet-lens/signet-lens && npm run compile`
- [ ] JavaScript SDK builds: `cd packages/sdk-js && npm run build`
- [ ] Workspace resolution works: `pnpm install` (after workspace setup)
- [ ] CI/CD pipelines pass with new paths

### Deployment Validation
- [ ] Docker build succeeds with new paths
- [ ] API endpoints respond correctly: `curl http://localhost:8088/healthz`
- [ ] Metrics endpoint accessible: `curl http://localhost:8088/metrics`

## Implementation Timeline

### Phase 1: Preparation (Day 1)
1. Create this plan and get approval
2. Ensure all tests pass in current structure
3. Create backup branch: `git branch backup-before-reorg`

### Phase 2: Core Moves (Day 1)
1. Execute git mv operations for server → apps/core-api
2. Update Python import paths and configurations
3. Test backend functionality

### Phase 3: Extension Consolidation (Day 1)
1. Move and consolidate VS Code extensions
2. Update extension build configurations
3. Test extension compilation

### Phase 4: SDK Reorganization (Day 1)
1. Move JavaScript SDK to packages/
2. Update TypeScript configurations
3. Test SDK builds

### Phase 5: Workspace Setup (Day 2)
1. Add workspace configuration files
2. Update CI/CD workflows
3. Test workspace functionality

### Phase 6: Validation & Documentation (Day 2)
1. Run full test suite
2. Update all documentation
3. Create draft PR

## Success Criteria

1. **Functionality Preserved:** All existing functionality works unchanged
2. **History Preserved:** Git history intact for all moved files
3. **CI/CD Green:** All workflows pass with new structure
4. **Documentation Updated:** All setup instructions reflect new structure
5. **Workspace Functional:** pnpm workspaces and turbo work correctly

## Approval Required

**⚠️ IMPORTANT:** This plan requires explicit approval before execution. The reorganization involves:
- Moving core backend code
- Restructuring VS Code extensions
- Updating CI/CD pipelines
- Changing development workflows

**Please review and approve before proceeding with implementation.**

---

**Next Steps After Approval:**
1. Execute Phase 1 moves
2. Update configurations
3. Validate functionality
4. Open draft PR for review
