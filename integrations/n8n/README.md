# n8n Integration for Signet Protocol

This provides an n8n community node allowing workflows to create verified exchanges, fetch receipt chains, export signed bundles, and retrieve billing dashboard data from a Signet Protocol server.

## Features
- Create Exchange (verified exchange with optional forward URL)
- Get Receipt Chain (by trace ID)
- Export Chain Bundle (signed export with signature headers)
- Get Billing Dashboard (usage & billing insights)
- Reload Reserved Capacity (admin reload of reserved config)
- Create Payment Link (Stripe billing link generation)

## Credentials
Configure the "Signet Protocol API" credential with:
- Signet URL (e.g. http://localhost:8088)
- API Key (maps to X-SIGNET-API-Key)

## Operations
| Operation | Description |
|-----------|-------------|
| Create Exchange | Creates a verified exchange producing a receipt |
| Get Receipt Chain | Retrieves full receipt chain for a trace ID |
| Export Chain Bundle | Exports signed bundle with signature headers |
| Get Billing Dashboard | Returns billing metrics and usage summary |
| Reload Reserved Capacity | Reloads reserved capacity configuration on server |
| Create Payment Link | Creates a Stripe payment link for tenant subscription |

## Development / Local Use
1. From repo root: `cd integrations/n8n`
2. Install deps: `npm install`
3. Build: `npm run build` (outputs to `dist/`)
4. Symlink or copy this folder into your n8n custom nodes directory (or set `N8N_CUSTOM_EXTENSIONS` to this path).
5. Restart n8n and add the credential + node in a workflow.

## Packaging & Publishing
The `package.json` is configured for publishing as a community node.

Steps:
1. Bump version: `npm version patch` (or minor / major)
2. Build (auto runs on publish): `npm publish --access public`
3. Create a Git tag and release (optional, if tracking versions in monorepo root).

Consumers can then install with:
```
npm install n8n-nodes-signet-protocol
```
and configure n8n to load community packages.

## Trace IDs & Idempotency
Trace ID auto-generates if not provided. Idempotency key is automatically generated per call to prevent duplicate exchanges.

## Error Handling
Errors are surfaced as n8n NodeOperationError or NodeApiError with context from the Signet API.

## Future Enhancements
- Pagination helper usage for future list endpoints
- Additional admin endpoints (policy validation, allowlist checks)
- Automatic policy / forward allowlist validation
- Tests (mocked HTTP) for node operations
