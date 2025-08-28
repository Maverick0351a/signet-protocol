# Changelog

All notable changes to this project will be documented in this file.

Format: Keep a top-level section per released artifact tag, grouping Added / Changed / Fixed / Removed. Unreleased changes accumulate under [Unreleased].

## [Unreleased]
- (placeholder)

## [signet-langchain-v0.1.0] - 2025-08-28
### Added
- Initial packaged LangChain integration (`signet-langchain`): callback handler, runnable wrapper, compatibility shim.
- PyPI publish workflow (`publish_langchain.yml`) triggered by tag `signet-langchain-v*`.

### Notes
- Mirrors existing in-repo implementation; future iterations may inline code instead of dynamic import shim.

## [v1.0.0] - 2025-08-28
### Added
- Frozen OpenAPI specification snapshot (`docs/api/openapi-v1.0.0.yaml`).
- Release workflow (`release.yml`) to attach versioned spec on tag push.

### Documentation
- README: Added stable spec link and versioning guidance.

### Integrity
- Establishes contract baseline for generated clients and integrations.

---

Reference tag naming:
- Core API/server spec: `v<MAJOR>.<MINOR>.<PATCH>`
- LangChain adapter: `signet-langchain-v<MAJOR>.<MINOR>.<PATCH>`

Breaking changes increment MAJOR; additive features increment MINOR; fixes / internal safe changes increment PATCH.
