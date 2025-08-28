# Changelog

All notable changes to the Signet Lens extension will be documented here.

## 1.0.3 - 2025-08-27
### Added
- Marketplace badges, screenshot placeholder, telemetry note.
- Bundled build (esbuild) with prod script.
- Icon included in package.

### Changed
- Moved runtime deps (axios, d3) into devDependencies and bundled output to slim runtime surface.
- Excluded entire node_modules from VSIX to reduce size.

## 1.0.2 - 2025-08-27
### Added
- Icon support and initial esbuild bundle.

### Changed
- Introduced bundling pipeline to prepare for dependency pruning.

## 1.0.1 - 2025-08-27
### Changed
- Updated publisher to `odinsecureai`.

## 1.0.0 - 2025-08-27
### Added
- Initial release with receipt verification, chain visualization, CID export/diff, inline decorations.
