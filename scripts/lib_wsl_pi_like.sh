#!/usr/bin/env bash
# Libreria comune per stack WSL Pi-like (sorgere da up/down/logs).
# shellcheck shell=bash

KOR35_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WSL_PI_STACK_DIR="${WSL_PI_STACK_DIR:-$KOR35_ROOT/config/docker/nginx-docker}"
WSL_PI_COMPOSE_FILE="${WSL_PI_COMPOSE_FILE:-docker-compose.wsl-pi.yml}"

wsl_pi_require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker non trovato. Installa Docker (o Docker Desktop WSL) e riprova." >&2
    return 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "docker compose non disponibile. Serve Docker Compose v2." >&2
    return 1
  fi
}

wsl_pi_compose() {
  (cd "$WSL_PI_STACK_DIR" && docker compose -f "$WSL_PI_COMPOSE_FILE" "$@")
}

wsl_pi_require_stack_dir() {
  if [ ! -d "$WSL_PI_STACK_DIR" ]; then
    echo "Directory stack non trovata: $WSL_PI_STACK_DIR" >&2
    return 1
  fi
}

wsl_pi_require_backend_link() {
  if [ ! -e "$WSL_PI_STACK_DIR/backend_src" ]; then
    echo "Manca il link backend_src nello stack. Esegui prima:" >&2
    echo "  $KOR35_ROOT/scripts/setup_wsl_pi_like.sh" >&2
    return 1
  fi
}
