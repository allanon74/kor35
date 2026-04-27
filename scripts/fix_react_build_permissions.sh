#!/usr/bin/env bash
# Ripristina la proprietà di react_build all'utente che esegue lo script (es. utente deploy SSH).
# Utile quando rsync/GitHub Actions fallisce con "Permission denied" sui file creati da Docker/root.
#
# Uso (sul server, dalla root del monorepo o passando il path):
#   ./scripts/fix_react_build_permissions.sh /srv/kor35 prod
#   ./scripts/fix_react_build_permissions.sh /home/pi/kor35-replica mirror
#
# Profili: prod | mirror (determina quale compose file usare per fermare il frontend).
# Opzionale: esporta COMPOSE_PROJECT_NAME se diverso da kor35-prod / kor35-replica.
set -euo pipefail

BASE="${1:?Path monorepo (es. /srv/kor35)}"
PROFILE="${2:-prod}"
RB="${BASE}/config/docker/nginx-docker/react_build"
CD="${BASE}/config/docker"

if [ ! -d "${CD}" ]; then
  echo "Directory compose non trovata: ${CD}" >&2
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

if [ -z "${COMPOSE_PROJECT_NAME:-}" ]; then
  if [ "${PROFILE}" = "mirror" ]; then
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kor35-replica}"
  else
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kor35-prod}"
  fi
fi

mkdir -p "${RB}"
cd "${CD}"

case "${PROFILE}" in
  prod)
    docker_cmd compose -f compose.base.yml -f compose.prod.yml stop frontend 2>/dev/null || true
    ;;
  mirror)
    docker_cmd compose -f compose.base.yml -f compose.mirror.yml stop frontend 2>/dev/null || true
    ;;
  *)
    echo "Profilo sconosciuto: ${PROFILE} (usa prod o mirror)" >&2
    exit 1
    ;;
esac

docker_cmd run --rm -v "${RB}:/mnt:rw" alpine:3.20 chown -R "$(id -u):$(id -g)" /mnt
echo "OK: ${RB} è di $(id -un):$(id -gn). Esegui rsync/deploy, poi avvia lo stack (docker compose up -d)."
