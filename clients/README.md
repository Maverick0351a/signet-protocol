# <div align="center"><img src="../assets/LogoSignet.png" alt="Signet Protocol Logo" width="300" /></div>

# Generated API Clients

This directory hosts (or receives) generated clients from the frozen OpenAPI specs under `docs/api/`.

Clients are produced via OpenAPI Generator and published as build artifacts (not committed) by the `generate-clients` workflow.

## Regenerate Locally

```bash
./scripts/generate_clients.sh 1.0.0
```

Outputs:
- `clients/python` – Python client (`signet_protocol_client`)
- `clients/typescript` – TypeScript Fetch client (`signet-protocol-client`)

## Workflow

Trigger manually:
```text
Actions > generate-clients > Run workflow (spec_version optional)
```

Artifacts include tarballs for Python & TypeScript clients.

## Version Mapping

Client version matches OpenAPI spec version (e.g. `openapi-v1.0.0.yaml` -> client package version 1.0.0). Bump spec & regenerate for new features.
