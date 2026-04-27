#!/usr/bin/env bash
# Ripristina la proprietà di frontend/ (es. node_modules scritto come root da Docker o da npm con sudo).
# Utile quando `npm ci` fallisce con EACCES su file sotto frontend/node_modules.
#
# Uso (sul server):
#   cd /srv/kor35 && ./scripts/fix_frontend_dir_permissions.sh
#   ./scripts/fix_frontend_dir_permissions.sh /srv/kor35
set -euo pipefail

if [ -n "${1:-}" ]; then
  BASE="$1"
elif [ -f "$(pwd)/config/docker/compose.base.yml" ]; then
  BASE="$(pwd)"
else
  echo "Uso: $0 [path-monorepo]" >&2
  echo "  Esempio: $0 /srv/kor35" >&2
  echo "  Oppure: cd /srv/kor35 && $0" >&2
  exit 1
fi

FE="${BASE}/frontend"
if [ ! -d "$FE" ]; then
  echo "Directory non trovata: $FE" >&2
  exit 1
fi

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  elif sudo -n docker info >/dev/null 2>&1; then
    sudo docker "$@"
  else
    echo "Errore: docker non raggiungibile (provare gruppo docker o sudo senza password)." >&2
    exit 1
  fi
}

docker_cmd run --rm -v "${FE}:/mnt:rw" alpine:3.20 chown -R "$(id -u):$(id -g)" /mnt
echo "OK: ${FE} è di $(id -un):$(id -gn)."
