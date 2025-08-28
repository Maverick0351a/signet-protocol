# n8n Integration for Signet Protocol

This provides an n8n community node allowing workflows to create verified exchanges, fetch receipt chains, export signed bundles, and retrieve billing dashboard data from a Signet Protocol server.

## Features
- Create Exchange (verified exchange with optional forward URL)
- Get Receipt Chain (by trace ID)
- Export Chain Bundle (signed export with signature headers)
- Get Billing Dashboard (usage & billing insights)

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

## Development
1. Copy `integrations/n8n/` into your custom n8n nodes directory or package scaffold.
2. Build (if bundling) and restart n8n.
3. Add credentials and test operations.

## Trace IDs & Idempotency
Trace ID auto-generates if not provided. Idempotency key is automatically generated per call to prevent duplicate exchanges.

## Error Handling
Errors are surfaced as n8n NodeOperationError or NodeApiError with context from the Signet API.

## Future Enhancements
- Pagination helper usage for future list endpoints
- Additional admin endpoints (reload reserved, etc.)
- Automatic policy / forward allowlist validation
