#!/usr/bin/env bash
# Libreria comune per stack WSL Pi-like (sorgere da up/down/logs).
# shellcheck shell=bash

KOR35_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WSL_PI_STACK_DIR="${WSL_PI_STACK_DIR:-$KOR35_ROOT/config/docker}"
WSL_PI_COMPOSE_BASE_FILE="${WSL_PI_COMPOSE_BASE_FILE:-compose.base.yml}"
WSL_PI_COMPOSE_FILE="${WSL_PI_COMPOSE_FILE:-compose.dev-home.yml}"
WSL_PI_ENV_PROFILE="${WSL_PI_ENV_PROFILE:-dev-home}"
KOR35_BACKEND_ENV_FILE="${KOR35_BACKEND_ENV_FILE:-$KOR35_ROOT/backend/.env}"

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
  (
    export KOR35_BACKEND_ENV_FILE
    cd "$WSL_PI_STACK_DIR" &&
    docker compose -f "$WSL_PI_COMPOSE_BASE_FILE" -f "$WSL_PI_COMPOSE_FILE" "$@"
  )
}

wsl_pi_require_stack_dir() {
  if [ ! -d "$WSL_PI_STACK_DIR" ]; then
    echo "Directory stack non trovata: $WSL_PI_STACK_DIR" >&2
    return 1
  fi
}

wsl_pi_require_backend_link() {
  if [ ! -f "$KOR35_ROOT/backend/manage.py" ]; then
    echo "Backend non trovato in $KOR35_ROOT/backend. Esegui prima:" >&2
    echo "  $KOR35_ROOT/scripts/setup_wsl_pi_like.sh" >&2
    return 1
  fi
}

wsl_pi_set_env_profile() {
  local profile="${1:-dev-home}"
  case "$profile" in
    dev-home)
      WSL_PI_ENV_PROFILE="dev-home"
      WSL_PI_COMPOSE_FILE="compose.dev-home.yml"
      KOR35_BACKEND_ENV_FILE="$KOR35_ROOT/backend/.env.dev-home"
      ;;
    dev-office)
      WSL_PI_ENV_PROFILE="dev-office"
      WSL_PI_COMPOSE_FILE="compose.dev-office.yml"
      KOR35_BACKEND_ENV_FILE="$KOR35_ROOT/backend/.env.dev-office"
      ;;
    mirror)
      WSL_PI_ENV_PROFILE="mirror"
      WSL_PI_COMPOSE_FILE="compose.mirror.yml"
      KOR35_BACKEND_ENV_FILE="$KOR35_ROOT/backend/.env.mirror"
      ;;
    prod)
      WSL_PI_ENV_PROFILE="prod"
      WSL_PI_COMPOSE_FILE="compose.prod.yml"
      KOR35_BACKEND_ENV_FILE="$KOR35_ROOT/backend/.env.prod"
      ;;
    *)
      echo "Profilo non valido: $profile" >&2
      echo "Valori ammessi: dev-home, dev-office, mirror, prod" >&2
      return 1
      ;;
  esac
}

wsl_pi_require_backend_env() {
  if [ ! -f "$KOR35_BACKEND_ENV_FILE" ]; then
    echo "File env backend mancante: $KOR35_BACKEND_ENV_FILE" >&2
    echo "Crea il file da template in config/env oppure usa scripts/use_env_backend.sh" >&2
    return 1
  fi
}
