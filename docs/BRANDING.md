# Signet Protocol Branding Assets

Central reference for logo usage across repositories, extensions, and generated artifacts.

## Current Assets

| File | Purpose | Notes |
|------|---------|-------|
| `assets/LogoSignet.png` | Primary dark-background logo | PNG uploaded (gradient). |

## Requested / Future Assets

| Target File | Dimensions | Purpose |
|-------------|------------|---------|
| `assets/LogoSignet-light.png` | Same aspect, optimized for light backgrounds | Used in light mode via `<picture>` source. |
| `vscode-extension/icon.png` | 128x128 (transparent) | Marketplace icon (square). |
| `assets/favicon/favicon-16.png` | 16x16 | Browser tab icon (future docs site) |
| `assets/favicon/favicon-32.png` | 32x32 | Browser tab icon (hi‑dpi) |
| `assets/favicon/favicon.svg` | Vector | Modern scalable favicon / PWA base |
| `assets/social-card.png` | 1200x630 | OpenGraph / social sharing card |

## Light/Dark Mode Usage

Root `README.md` uses a `<picture>` wrapper prepared for dark/light differentiation. After adding `LogoSignet-light.png`, update the markup to:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/LogoSignet.png">
  <source media="(prefers-color-scheme: light)" srcset="./assets/LogoSignet-light.png">
  <img src="./assets/LogoSignet.png" alt="Signet Protocol Logo" width="420" />
</picture>
```

## Creating Derivatives (CLI Examples)

Assuming you have the source logo as `logo-source.png` (transparent background preferred):

```bash
# Generate 128x128 extension icon
magick logo-source.png -resize 128x128 -background none -gravity center -extent 128x128 vscode-extension/icon.png

# Generate light variant (e.g., lighten text or add subtle outline) – placeholder example
magick logo-source.png -fill white -tint 5 assets/LogoSignet-light.png

# Favicons
mkdir -p assets/favicon
magick logo-source.png -resize 32x32 assets/favicon/favicon-32.png
magick logo-source.png -resize 16x16 assets/favicon/favicon-16.png

# SVG optimization (if you have vector original)
svgo logo-source.svg -o assets/favicon/favicon.svg
```

## VS Code Extension Icon Notes

Marketplace guidelines recommend a clear, padded 128x128 PNG. The current `icon.png` can be replaced with the processed square variant—after replacing, bump `version` in `vscode-extension/package.json` and publish.

## Social Card (OG Image)

Add `assets/social-card.png` (1200x630) for richer link unfurls. Include at top of `README.md` using:

```markdown
<!-- OpenGraph: place in repository for external docs site build -->
```

If a docs site (e.g., Docusaurus) is added later, configure meta tags referencing the card.

## Attribution & License

Logo and brand assets © ODIN Protocol Corporation. Distributed under the project license for inclusion with the software; not for unrelated commercial reuse without permission.

## Checklist (Status)

- [x] Primary dark logo PNG
- [ ] Light-mode PNG (generated placeholder if script run without custom source)
- [ ] 128x128 extension icon (script outputs to vscode-extension/icon.png)
- [ ] Favicon set (16/32/SVG) (script produces 16/32 PNGs)
- [ ] Social card (script creates placeholder social-card.png)

Run `./scripts/prepare_branding_assets.sh` to generate provisional assets.

Once these items are complete, remove unchecked placeholders and update this checklist.
