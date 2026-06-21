#!/usr/bin/env bash
set -euo pipefail

# Esegue mirror_network_check.sh sul Pi via SSH (da PC sviluppatore / agente Cursor).
#
# Porta SSH pubblica mirror: 10022 (kor35.ddns.net → Pi:22).
#
# Prerequisiti (~/.ssh/config) — vedi anche config/mirror/ssh-config.example:
#   Host kor35-mirror
#     HostName kor35.ddns.net
#     User pi
#     Port 10022
#     IdentityFile ~/.ssh/id_ed25519
#
# Uso:
#   ./scripts/mirror_ssh_check.sh
#   MIRROR_SSH_IDENTITY=~/.ssh/id_ed25519 ./scripts/mirror_ssh_check.sh
#   ./scripts/mirror_ssh_check.sh kor35-mirror
#   MIRROR_SSH_HOST=192.168.1.50 MIRROR_SSH_PORT=22 ./scripts/mirror_ssh_check.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SSH_TARGET="${1:-}"
SSH_PORT="${MIRROR_SSH_PORT:-10022}"
SSH_USER="${MIRROR_SSH_USER:-pi}"
SSH_HOST="${MIRROR_SSH_HOST:-kor35.ddns.net}"
REMOTE_REPO="${MIRROR_REPO_PATH:-/home/pi/kor35-replica}"

ssh_args=(-o BatchMode=yes -o ConnectTimeout=15)
if [ -n "${MIRROR_SSH_IDENTITY:-}" ]; then
  ssh_args+=(-i "$MIRROR_SSH_IDENTITY")
fi

if [ -z "$SSH_TARGET" ]; then
  if [ -f "${HOME}/.ssh/config" ] && grep -qE '^[[:space:]]*Host[[:space:]]+kor35-mirror\b' "${HOME}/.ssh/config"; then
    SSH_TARGET="kor35-mirror"
  else
    SSH_TARGET="${SSH_USER}@${SSH_HOST}"
    ssh_args+=(-p "$SSH_PORT")
  fi
fi

echo "[mirror_ssh_check] SSH → ${SSH_TARGET}"
ssh "${ssh_args[@]}" "$SSH_TARGET" \
  "cd '${REMOTE_REPO}' && ./scripts/mirror_network_check.sh"
