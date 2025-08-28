# Signet Chat + Lens (VS Code Extension)

Secure Copilot‑style chat plus receipt chain verification UI powered by Signet Protocol.

## Features (Preview)
* Chat panel: send JSON exchanges through `/v1/exchange`.
* Lens panel: export & inspect receipt bundles by `trace_id`.
* Secure key storage via VS Code SecretStorage.
* Agent descriptor scaffold (define custom agent endpoints).

## Setup
1. Install dependencies:
```bash
npm install
```
2. Compile:
```bash
npm run compile
```
3. Press F5 to launch the extension host.

## Commands
| Command | Purpose |
|---------|---------|
| Signet: Open Chat | Opens chat webview |
| Signet: Open Lens | Opens lens / bundle viewer |
| Signet: Configure API & Key | Stores base URL + API key securely |
| Signet: Add Agent Descriptor | Inserts JSON template for an agent |

## Configuration
| Setting | Description |
|---------|-------------|
| `signet.apiBase` | Base URL (e.g. https://signet-protocol.fly.dev) |
| `signet.tenant` | Tenant / namespace (optional) |
| `signet.telemetry` | Allow anonymous usage telemetry |

## Security
API key stored only in SecretStorage (encrypted on disk). No receipt content leaves your machine unless you send it.

## Roadmap
* Inline receipt diffing
* CID recompute inside lens
* Entitlement (tier) indicator via `/v1/entitlements`
* Billing usage gauge (`/v1/billing/dashboard`)

## License
Apache 2.0
