#!/usr/bin/env bash
# SSH verso mirror Pi — libreria condivisa (PC dev / agenti Cursor).
# shellcheck shell=bash

mirror_ssh_repo_path() {
  echo "${MIRROR_REPO_PATH:-/home/pi/kor35-replica}"
}

mirror_ssh_build_args() {
  MIRROR_SSH_ARGS=(-o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new)
  if [ -f "${HOME}/.ssh/known_hosts" ]; then
    MIRROR_SSH_ARGS+=(-o "UserKnownHostsFile=${HOME}/.ssh/known_hosts")
  fi
  if [ -n "${MIRROR_SSH_IDENTITY:-}" ]; then
    MIRROR_SSH_ARGS+=(-i "$MIRROR_SSH_IDENTITY")
  fi

  MIRROR_SSH_TARGET="${MIRROR_SSH_TARGET:-}"
  if [ -z "$MIRROR_SSH_TARGET" ]; then
    if [ -f "${HOME}/.ssh/config" ] && grep -qE '^[[:space:]]*Host[[:space:]]+kor35-mirror\b' "${HOME}/.ssh/config"; then
      MIRROR_SSH_TARGET="kor35-mirror"
    else
      MIRROR_SSH_TARGET="${MIRROR_SSH_USER:-pi}@${MIRROR_SSH_HOST:-kor35.ddns.net}"
      MIRROR_SSH_ARGS+=(-p "${MIRROR_SSH_PORT:-10022}")
    fi
  fi
}

mirror_ssh_run() {
  local remote_cmd="$1"
  mirror_ssh_build_args
  echo "[mirror-pi] SSH → ${MIRROR_SSH_TARGET}"
  # shellcheck disable=SC2029
  ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_TARGET" "$remote_cmd"
}

mirror_ssh_require_connection() {
  mirror_ssh_build_args
  if ! ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_TARGET" 'echo ok' >/dev/null 2>&1; then
    echo "[mirror-pi] ERRORE: SSH fallito verso ${MIRROR_SSH_TARGET}" >&2
    echo "Configura ~/.ssh/config (config/mirror/ssh-config.example) e authorized_keys sul Pi." >&2
    return 1
  fi
}
