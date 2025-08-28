# Signet Lens VS Code Extension

Visualize and verify Signet Protocol receipt chains directly inside VS Code.

## Features
* Verify a receipt chain integrity (hash links) locally
* Fetch full chain by trace id from a running Signet server
* Visualize hops in a side panel & webview
* Copy bundle CID (via export API) for provenance workflows
* Inline decorations for verified receipts (hash, hop, status)
* Diff locally calculated CID with a provided one

## Commands ("Signet Lens" prefix)
* Verify Receipt Chain
* Visualize Receipt Chain
* Copy Bundle CID
* Diff CID
* Open Settings

## Settings
| Setting | Description | Default |
|---------|-------------|---------|
| serverUrl | Base URL of Signet backend | http://localhost:8088 |
| apiKey | API key used for authenticated endpoints | (empty) |
| autoVerify | Auto-verify JSON receipts on focus/change | true |
| showInlineDecorations | Show inline hash / hop metadata | true |
| highlightReceiptFields | Highlight receipt specific fields | true |

## Requirements
Run a Signet Protocol backend (see project README) and obtain an API key present in the server configuration.

## Publishing
1. Login once: `vsce login odin-protocol`
2. Bump version in `package.json` (Marketplace forbids reusing versions)
3. Package test: `npm run package` (produces .vsix)
4. Publish: `npm run publish`

## License
Apache-2.0 © 2025 ODIN Protocol Corporation
