#!/usr/bin/env bash
# SSH verso la produzione (www.kor35.it). Usa l'alias kor35-prod se c'è,
# altrimenti deploy@www.kor35.it con ~/.ssh/id_docker.
# shellcheck shell=bash

prod_ssh_build_args() {
  PROD_SSH_ARGS=(-o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new)
  if [ -f "${HOME}/.ssh/known_hosts" ]; then
    PROD_SSH_ARGS+=(-o "UserKnownHostsFile=${HOME}/.ssh/known_hosts")
  fi

  local identity="${PROD_SSH_IDENTITY:-}"
  if [ -z "$identity" ] && [ -f "${HOME}/.ssh/id_docker" ]; then
    identity="${HOME}/.ssh/id_docker"
  fi
  if [ -n "$identity" ]; then
    PROD_SSH_ARGS+=(-i "$identity" -o IdentitiesOnly=yes)
  fi

  if [ -n "${PROD_SSH_TARGET:-}" ]; then
    PROD_SSH_EFFECTIVE_TARGET="$PROD_SSH_TARGET"
  elif [ -f "${HOME}/.ssh/config" ] && grep -qE '^[[:space:]]*Host[[:space:]]+kor35-prod\b' "${HOME}/.ssh/config"; then
    PROD_SSH_EFFECTIVE_TARGET="kor35-prod"
  else
    PROD_SSH_EFFECTIVE_TARGET="${PROD_SSH_USER:-deploy}@${PROD_SSH_HOST:-www.kor35.it}"
  fi
}

prod_ssh_run() {
  local remote_cmd="$1"
  prod_ssh_build_args
  echo "[prod] SSH → ${PROD_SSH_EFFECTIVE_TARGET}"
  # shellcheck disable=SC2029
  ssh "${PROD_SSH_ARGS[@]}" "$PROD_SSH_EFFECTIVE_TARGET" "$remote_cmd"
}
