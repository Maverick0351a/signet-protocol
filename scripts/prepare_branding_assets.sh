#!/usr/bin/env bash
set -euo pipefail

SRC=${1:-assets/LogoSignet.png}
OUT_ICON=vscode-extension/icon.png
LIGHT=assets/LogoSignet-light.png
FAVICON_DIR=assets/favicon
SOCIAL=assets/social-card.png

echo "[branding] Source: $SRC"
command -v magick >/dev/null 2>&1 || { echo "ImageMagick 'magick' command required"; exit 1; }

mkdir -p "$FAVICON_DIR"

echo "[branding] Generating 128x128 extension icon -> $OUT_ICON"
magick "$SRC" -resize 128x128 -background none -gravity center -extent 128x128 "$OUT_ICON"

if [ ! -f "$LIGHT" ]; then
  echo "[branding] Creating provisional light variant (same as dark) -> $LIGHT"
  cp "$SRC" "$LIGHT"
  echo "   Replace $LIGHT with a true light-mode optimized version when available." 
fi

echo "[branding] Generating favicons"
magick "$SRC" -resize 32x32 "$FAVICON_DIR/favicon-32.png"
magick "$SRC" -resize 16x16 "$FAVICON_DIR/favicon-16.png"

if command -v convert >/dev/null 2>&1; then :; fi

if [ ! -f "$SOCIAL" ]; then
  echo "[branding] Creating placeholder social card $SOCIAL"
  magick "$SRC" -resize 800x800 -background '#0A1320' -gravity center -extent 1200x630 -font Arial -pointsize 48 -fill white -gravity south -annotate +0+40 'Signet Protocol' "$SOCIAL" || true
fi

echo "[branding] Done. Review generated assets and commit:"
echo "   git add $OUT_ICON $LIGHT $FAVICON_DIR favicon-* $SOCIAL"
echo "   git commit -m 'chore(branding): update generated assets'"
