#!/usr/bin/env bash
# Genera la foreground dell'icona Wear OS dal logo KOR35 (stessi asset usati da PWA / Django).
# Usa il primo file esistente tra i candidati (ordine di preferenza).
# Opzionale: ImageMagick (magick o convert) per ritaglio e resize a 432×432 (safe zone adaptive icon).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEAR="${ROOT}/extra/local-artifacts/wearos-kor35"
RES="${WEAR}/app/src/main/res"

# PWA (index.html, header) → icone manifest PWA → static Django (base.html)
SRC_CANDIDATES=(
  "${ROOT}/frontend/public/Logo Kor-AD.png"
  "${ROOT}/frontend/public/Logo Kor-AD_Trasp.png"
  "${ROOT}/frontend/public/pwa-512x512.png"
  "${ROOT}/frontend/public/pwa-192x192.png"
  "${ROOT}/frontend/public/logo.png"
  "${ROOT}/frontend/public/icon.png"
  "${ROOT}/frontend/public/favicon.png"
  "${ROOT}/backend/static/tema/logo.png"
)

SRC=""
for f in "${SRC_CANDIDATES[@]}"; do
  if [[ -f "$f" ]]; then
    SRC="$f"
    break
  fi
done

if [[ -z "$SRC" ]]; then
  echo "Nessun logo trovato. Aggiungi almeno uno di:" >&2
  for f in "${SRC_CANDIDATES[@]}"; do echo "  - $f" >&2; done
  exit 1
fi

PNG_OUT="${RES}/drawable/kor35_launcher_logo.png"
mkdir -p "$(dirname "$PNG_OUT")"

if command -v magick >/dev/null 2>&1; then
  magick "$SRC" -trim -resize "432x432" -background none -gravity center -extent "432x432" "$PNG_OUT"
elif command -v convert >/dev/null 2>&1; then
  convert "$SRC" -trim -resize "432x432" -background none -gravity center -extent "432x432" "$PNG_OUT"
else
  echo "ImageMagick non trovato: installa imagemagick (magick/convert) oppure crea manualmente:" >&2
  echo "  $PNG_OUT  (432×432 px, PNG con trasparenza se serve)" >&2
  exit 1
fi

cat > "${RES}/drawable/ic_launcher_foreground.xml" <<'XML'
<?xml version="1.0" encoding="utf-8"?>
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item>
        <bitmap
            android:gravity="center"
            android:src="@drawable/kor35_launcher_logo" />
    </item>
</layer-list>
XML

echo "Icona Wear aggiornata dal logo web:"
echo "  sorgente: $SRC"
echo "  PNG:      $PNG_OUT"
echo "Commit drawable/kor35_launcher_logo.png e drawable/ic_launcher_foreground.xml se vuoi versionarli."
