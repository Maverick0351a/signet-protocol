# Favicon & Web App Icons (Placeholder)

Generate these files using `scripts/prepare_branding_assets.sh` once ImageMagick is installed:

Expected files:
- favicon-16.png
- favicon-32.png
- favicon.svg (optional vector)
- site.webmanifest (optional PWA manifest)

Example HTML snippet (for future docs site):
```html
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon/favicon-32.png" />
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon/favicon-16.png" />
<link rel="icon" type="image/svg+xml" href="/assets/favicon/favicon.svg" />
<link rel="manifest" href="/assets/favicon/site.webmanifest" />
```

Run script:
```bash
./scripts/prepare_branding_assets.sh
```

Add and commit generated assets afterwards.
