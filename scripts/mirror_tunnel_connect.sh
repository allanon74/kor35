#!/usr/bin/env bash
# Tiene aperta la galleria SSH dal Pi verso la produzione.
# Il forward è 127.0.0.1:18443 sul server prod → HTTPS locale del Pi.
set -euo pipefail

ENV_FILE="${MIRROR_TUNNEL_ENV:-/etc/kor35/mirror-tunnel.env}"
KEY_FILE="${MIRROR_TUNNEL_KEY:-/etc/kor35/mirror-tunnel/id_ed25519}"
KNOWN_HOSTS="${MIRROR_TUNNEL_KNOWN_HOSTS:-/etc/kor35/mirror-tunnel/known_hosts}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Manca ${ENV_FILE}. Esegui: sudo ./scripts/install_mirror_tunnel.sh" >&2
  exit 1
fi
if [ ! -f "$KEY_FILE" ]; then
  echo "Manca la chiave ${KEY_FILE}." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

: "${MIRROR_TUNNEL_SSH_HOST:?}"
: "${MIRROR_TUNNEL_SSH_PORT:?}"
: "${MIRROR_TUNNEL_SSH_USER:?}"
: "${MIRROR_TUNNEL_REMOTE_PORT:?}"
: "${MIRROR_TUNNEL_LOCAL_PORT:?}"

# HTTPS del Pi (sito) e, se configurata, la sua SSH.
# La SSH resta su 127.0.0.1 del server prod: GitHub ci arriva con un salto, non da Internet.
FORWARDS=(-R "127.0.0.1:${MIRROR_TUNNEL_REMOTE_PORT}:127.0.0.1:${MIRROR_TUNNEL_LOCAL_PORT}")
if [ -n "${MIRROR_TUNNEL_SSH_REMOTE_PORT:-}" ]; then
  local_ssh="${MIRROR_TUNNEL_SSH_LOCAL_PORT:-22}"
  FORWARDS+=(-R "127.0.0.1:${MIRROR_TUNNEL_SSH_REMOTE_PORT}:127.0.0.1:${local_ssh}")
fi

exec ssh -4 -N -T \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile="$KNOWN_HOSTS" \
  -o IdentitiesOnly=yes \
  -o IdentityFile="$KEY_FILE" \
  -p "$MIRROR_TUNNEL_SSH_PORT" \
  "${FORWARDS[@]}" \
  "${MIRROR_TUNNEL_SSH_USER}@${MIRROR_TUNNEL_SSH_HOST}"
