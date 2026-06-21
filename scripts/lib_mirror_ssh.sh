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

  local identity="${MIRROR_SSH_IDENTITY:-}"
  if [ -z "$identity" ] && [ -f "${HOME}/.ssh/id_docker" ]; then
    identity="${HOME}/.ssh/id_docker"
  fi
  if [ -n "$identity" ]; then
    MIRROR_SSH_ARGS+=(-i "$identity" -o IdentitiesOnly=yes)
  fi

  # Target risolto a ogni chiamata (non riusare MIRROR_SSH_TARGET tra invocazioni — perderebbe -p 10022).
  local explicit_target="${MIRROR_SSH_TARGET:-}"
  local effective_target=""
  local needs_port=0

  if [ -n "$explicit_target" ]; then
    effective_target="$explicit_target"
    if [ "$explicit_target" != "kor35-mirror" ]; then
      needs_port=1
    fi
  elif [ -f "${HOME}/.ssh/config" ] && grep -qE '^[[:space:]]*Host[[:space:]]+kor35-mirror\b' "${HOME}/.ssh/config"; then
    effective_target="kor35-mirror"
  else
    effective_target="${MIRROR_SSH_USER:-pi}@${MIRROR_SSH_HOST:-kor35.ddns.net}"
    needs_port=1
  fi

  if [ "$needs_port" = "1" ]; then
    MIRROR_SSH_ARGS+=(-p "${MIRROR_SSH_PORT:-10022}")
  fi

  MIRROR_SSH_EFFECTIVE_TARGET="$effective_target"
}

mirror_ssh_run() {
  local remote_cmd="$1"
  mirror_ssh_build_args
  echo "[mirror-pi] SSH → ${MIRROR_SSH_EFFECTIVE_TARGET}"
  # shellcheck disable=SC2029
  ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_EFFECTIVE_TARGET" "$remote_cmd"
}

mirror_ssh_require_connection() {
  mirror_ssh_build_args
  if ! ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_EFFECTIVE_TARGET" 'echo ok' >/dev/null 2>&1; then
    echo "[mirror-pi] ERRORE: SSH fallito verso ${MIRROR_SSH_EFFECTIVE_TARGET}" >&2
    echo "Prova: ssh -o BatchMode=yes -p 10022 -i ~/.ssh/id_docker pi@kor35.ddns.net 'hostname'" >&2
    echo "Template opzionale: config/mirror/ssh-config.example" >&2
    return 1
  fi
}
