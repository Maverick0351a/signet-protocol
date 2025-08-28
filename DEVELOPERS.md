# Developer Guide

Internal / advanced notes moved out of the user‑oriented `README.md`.

## Release & Publishing Workflows

Tag formats:
- Core release: `vX.Y.Z` (triggers Docker build + release notes)
- LangChain adapter: `signet-langchain-vX.Y.Z`
- TypeScript client: `client-ts-vX.Y.Z`
- Python client: `client-py-vX.Y.Z`
- VS Code extension: `vscode-extension-vX.Y.Z`

Workflows under `.github/workflows/`:
- `pre_release.yml` – Validates changelog + spec snapshot before tagging
- `docker_publish.yml` – Builds & scans (Trivy) the container image
- `publish_langchain.yml` – Publishes `signet-langchain` to PyPI
- `publish_ts_client.yml` / `publish_python_client.yml` – Generate + publish clients
- `publish_extension.yml` – Publishes Signet Lens to Marketplace
- `generate_clients.yml` – Artifact-only client generation (no publish)

## Client Generation (Manual)
```bash
./scripts/generate_clients.sh 1.0.0
```
Outputs under `clients/` (ignored from VCS). Frozen specs live in `docs/api/openapi-<version>.yaml`.

## Dependency Pinning & Upgrade Policy
Selective pinning balances stability and security.
- OpenAI SDK pinned awaiting 1.x migration.
- OpenTelemetry core/instrumentation pinned together.
- FastAPI / Starlette / Pydantic upgraded in coordinated batches.
- Security updates applied promptly via Dependabot.

## Test & Lint
```bash
pytest tests/ -q
ruff check .
```
CI enforces lint; trivial fixes auto-applied on direct pushes to `main`.

## Metrics & Tracing
Prometheus metrics surface exchange pipeline, billing, fallback, capacity and latency. Keep new metrics consistent: `signet_<domain>_<noun>_{total|seconds}`. Histograms use `_seconds` suffix; counters use `_total`.

OpenTelemetry spans: `exchange.phase.<name>` plus `billing.enqueue`, `fallback.repair` etc. Add attributes rather than creating new span names when possible.

## Architecture Notes
Core pipeline phases (simplified):
1. sanitize
2. canonicalize
3. transform (tool -> target normalization)
4. sign (receipt)
5. forward (optional) / store audit

Each phase should expose: timing span, error classification, metrics count/inc (success / failure), and structured log with correlation id.

## Branding Asset Workflow
Run `./scripts/prepare_branding_assets.sh` after updating `assets/LogoSignet.png` to regenerate light variant, favicons, social card placeholder and extension icon. Commit replacements (do not commit vsix packages).

## Local Docker Build
```bash
docker build -t signet:dev .
docker run --rm -p 8088:8088 signet:dev
```

## Release Checklist (High Level)
- [ ] Update CHANGELOG.md
- [ ] Freeze spec snapshot `docs/api/openapi-<new>.yaml`
- [ ] Run pre-release workflow (must pass)
- [ ] Tag core repo `v<version>`
- [ ] (Optional) Tag client & adapter versions if API changes require
- [ ] Verify Docker image + scan results
- [ ] Publish docs updates / social card

## Conventions
- JSON canonicalization: RFC 8785 (never mutate canonical form after sign)
- Receipt hash algorithm: `sha256`
- All receipts must be forward-compatible (additive fields only)

## Future Enhancements (Engineering Backlog)
- Threat model document
- Additional adapters (CrewAI, LlamaIndex, AutoGen) packaged & published
- Formal semantic invariant DSL
- Multi-region key rotation service

---
Questions for maintainers? Open an issue with the label `maintenance`.
