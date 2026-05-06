#!/usr/bin/env bash
set -euo pipefail

# Avvia lo stack WSL Pi-like (Nginx + Gunicorn + Daphne + Postgres + Redis).
# Opzioni:
#   --env <nome> profilo ambiente: dev-home | dev-office | mirror | prod
#   --setup      esegue prima setup_wsl_pi_like.sh (build frontend + symlink)
#   --no-build   non passa --build a docker compose up (riavvio veloce)
#   --skip-collectstatic non esegue collectstatic dopo l'avvio
#   --recreate-frontend forza recreate del solo servizio frontend (utile dopo reboot WSL/Docker Desktop)
#   --allow-db-reinit consente ri-inizializzazione DB quando il volume atteso non esiste (override esplicito)
#   Altri argomenti vengono passati a: docker compose up -d

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_wsl_pi_like.sh
source "$SCRIPT_DIR/lib_wsl_pi_like.sh"

DO_SETUP=false
BUILD_FLAG=(--build)
RUN_COLLECTSTATIC=true
RECREATE_FRONTEND=false
ALLOW_DB_REINIT=false
COMPOSE_EXTRA=()
ENV_PROFILE="dev-home"

while [ $# -gt 0 ]; do
  case "$1" in
    --env)
      ENV_PROFILE="${2:-}"
      if [ -z "$ENV_PROFILE" ]; then
        echo "--env richiede un valore" >&2
        exit 1
      fi
      shift 2
      ;;
    --setup)
      DO_SETUP=true
      shift
      ;;
    --no-build)
      BUILD_FLAG=()
      shift
      ;;
    --skip-collectstatic)
      RUN_COLLECTSTATIC=false
      shift
      ;;
    --recreate-frontend)
      RECREATE_FRONTEND=true
      shift
      ;;
    --allow-db-reinit)
      ALLOW_DB_REINIT=true
      shift
      ;;
    --)
      shift
      COMPOSE_EXTRA+=("$@")
      break
      ;;
    *)
      COMPOSE_EXTRA+=("$1")
      shift
      ;;
  esac
done

wsl_pi_set_env_profile "$ENV_PROFILE"
wsl_pi_require_docker
wsl_pi_require_stack_dir

DB_VOLUME_NAME=""
STATE_DIR="$KOR35_ROOT/.runtime-state"
STATE_FILE="$STATE_DIR/db-volume-ready-$WSL_PI_ENV_PROFILE"

case "$WSL_PI_ENV_PROFILE" in
  dev-home)
    DB_VOLUME_NAME="kor35_devhome_postgres_data"
    ;;
  dev-office)
    DB_VOLUME_NAME="kor35_devoffice_postgres_data"
    ;;
esac

if [ -n "$DB_VOLUME_NAME" ] && [ -f "$STATE_FILE" ]; then
  if ! docker volume inspect "$DB_VOLUME_NAME" >/dev/null 2>&1; then
    if [ "$ALLOW_DB_REINIT" = false ]; then
      echo "ERRORE: volume DB atteso non trovato: $DB_VOLUME_NAME" >&2
      echo "Protezione anti-reset attiva: blocco avvio per evitare initdb accidentale." >&2
      echo "Se vuoi davvero ripartire da DB vuoto, rilancia con --allow-db-reinit." >&2
      exit 1
    fi
    echo "ATTENZIONE: override attivo (--allow-db-reinit), procedo anche senza volume DB precedente."
  fi
fi

if [ "$DO_SETUP" = true ]; then
  "$SCRIPT_DIR/setup_wsl_pi_like.sh"
else
  wsl_pi_require_backend_link || exit 1
fi
wsl_pi_require_backend_env || exit 1

echo "Avvio stack [$WSL_PI_ENV_PROFILE] in $WSL_PI_STACK_DIR ..."
wsl_pi_compose up -d "${BUILD_FLAG[@]}" "${COMPOSE_EXTRA[@]}"

if [ "$RECREATE_FRONTEND" = true ]; then
  echo "Forzo recreate del servizio frontend..."
  wsl_pi_compose up -d --force-recreate frontend
fi

if [ "$RUN_COLLECTSTATIC" = true ]; then
  echo "Eseguo collectstatic nel container backend..."
  wsl_pi_compose exec -T backend python manage.py collectstatic --noinput
fi

if [ -n "$DB_VOLUME_NAME" ]; then
  if docker volume inspect "$DB_VOLUME_NAME" >/dev/null 2>&1; then
    mkdir -p "$STATE_DIR"
    touch "$STATE_FILE"
  fi
fi

echo ""
echo "Stack avviato (profilo: $WSL_PI_ENV_PROFILE)."
echo "Log: $SCRIPT_DIR/logs_wsl_pi_like.sh"
echo "Stop: $SCRIPT_DIR/down_wsl_pi_like.sh"
