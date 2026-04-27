#!/usr/bin/env bash
# Verifica sul server che index.html punti solo a file presenti in assets/ (evita SPA rotta dopo deploy).
# Uso (sulla macchina dove gira nginx / bind mount react_build):
#   cd /srv/kor35 && ./scripts/verify_react_build_consistency.sh
#   ./scripts/verify_react_build_consistency.sh /srv/kor35/config/docker/nginx-docker/react_build
# Exit 0 se tutto ok, 1 se manca almeno un file.
set -euo pipefail

if [ -n "${1:-}" ]; then
  RB="$1"
elif [ -f "$(pwd)/config/docker/compose.base.yml" ]; then
  RB="$(pwd)/config/docker/nginx-docker/react_build"
else
  echo "Uso: $0 [path-a/react_build]" >&2
  echo "  Esempio: $0 /srv/kor35/config/docker/nginx-docker/react_build" >&2
  echo "  Oppure: cd /srv/kor35 && $0" >&2
  exit 1
fi

if [ ! -f "${RB}/index.html" ]; then
  echo "ERRORE: manca ${RB}/index.html" >&2
  exit 1
fi

missing=0
while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  # rel tipo /assets/index-abc.js
  f="${RB}${rel}"
  if [ ! -f "$f" ]; then
    echo "ERRORE: manca file referenziato da index.html: $f" >&2
    missing=1
  fi
done < <({ grep -oE '(src|href)="/assets/[^"]+"' "${RB}/index.html" || true; } | sed -E 's/^(src|href)="//;s/"$//' | sort -u)

if [ "$missing" -ne 0 ]; then
  echo "Verifica fallita: correggere permessi (scripts/fix_react_build_permissions.sh) e rifare rsync/build." >&2
  exit 1
fi

echo "OK: index.html e asset in ${RB}/assets sono allineati."
ls -la "${RB}/assets/index"*.js "${RB}/assets/index"*.css 2>/dev/null || true
