#!/usr/bin/env bash
# Ripristina la proprietà di frontend/ e apps/card-studio/ (node_modules/dist scritti come root).
# Utile quando `npm ci` o `git reset --hard` falliscono con EACCES/Permission denied.
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

OWNER_UID="$(id -u)"
OWNER_GID="$(id -g)"
fixed=0
for rel in frontend frontend-pilot apps/card-studio; do
  target="${BASE}/${rel}"
  if [ ! -d "$target" ]; then
    continue
  fi
  docker_cmd run --rm -v "${target}:/mnt:rw" alpine:3.20 chown -R "${OWNER_UID}:${OWNER_GID}" /mnt
  echo "OK: ${target} è di $(id -un):$(id -gn)."
  fixed=$((fixed + 1))
done

if [ "${fixed}" -eq 0 ]; then
  echo "Nessuna directory frontend/card-studio trovata sotto ${BASE}" >&2
  exit 1
fi
