#!/usr/bin/env bash
set -euo pipefail

# Prepara l'ambiente WSL "Pi-like" in config/docker/nginx-docker:
# - directory dati (db/static/media) e react_build
# - build frontend e copia in react_build (se npm disponibile o --skip-frontend-build)
#
# Opzioni:
#   --skip-frontend-build   non esegue npm (server senza Node: popola react_build da altrove o usa deploy GitHub)

SKIP_FRONTEND_BUILD=false
while [ $# -gt 0 ]; do
  case "$1" in
    --skip-frontend-build)
      SKIP_FRONTEND_BUILD=true
      shift
      ;;
    -h|--help)
      echo "Uso: $0 [--skip-frontend-build]"
      echo "  Senza npm sul sistema: $0 --skip-frontend-build"
      echo "  Poi copia frontend/dist in config/docker/nginx-docker/react_build/ (o attendi deploy CI)."
      exit 0
      ;;
    *)
      echo "Opzione sconosciuta: $1 (usa --help)" >&2
      exit 1
      ;;
  esac
done

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_DIR="$ROOT_DIR/config/docker/nginx-docker"
BACKEND_DIR="$ROOT_DIR/backend"
if [ -d "$ROOT_DIR/frontend" ]; then
  FRONTEND_DIR="$ROOT_DIR/frontend"
else
  FRONTEND_DIR="/home/django/progetti/kor35-app"
fi

echo "ROOT_DIR=$ROOT_DIR"
echo "STACK_DIR=$STACK_DIR"
echo "FRONTEND_DIR=$FRONTEND_DIR"

if [ ! -d "$STACK_DIR" ]; then
  echo "Directory stack non trovata: $STACK_DIR" >&2
  exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "Directory frontend non trovata: $FRONTEND_DIR" >&2
  exit 1
fi

mkdir -p "$STACK_DIR/postgres_data" "$STACK_DIR/static_data" "$STACK_DIR/media_data" "$STACK_DIR/react_build"

if [ ! -d "$BACKEND_DIR" ] || [ ! -f "$BACKEND_DIR/manage.py" ]; then
  echo "Backend non trovato in: $BACKEND_DIR" >&2
  exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
  if [ -f "$ROOT_DIR/.env" ]; then
    cp "$ROOT_DIR/.env" "$BACKEND_DIR/.env"
    echo "Creato $BACKEND_DIR/.env da $ROOT_DIR/.env"
  elif [ -f "$ROOT_DIR/.env.wsl.example" ]; then
    cp "$ROOT_DIR/.env.wsl.example" "$BACKEND_DIR/.env"
    echo "Creato $BACKEND_DIR/.env da $ROOT_DIR/.env.wsl.example"
  fi
fi

if [ "$SKIP_FRONTEND_BUILD" = true ]; then
  echo ""
  echo "Build frontend SALTATA (--skip-frontend-build)."
  echo "Cartella react_build: $STACK_DIR/react_build"
  echo "Popolala con una di queste opzioni:"
  echo "  - deploy GitHub Actions su main (rsync automatico di frontend/dist)"
  echo "  - da PC con npm: (cd frontend && npm ci && npm run build) poi rsync dist/ verso il server"
  echo "  - installare Node sul server e rilanciare questo script senza --skip-frontend-build"
  echo ""
elif ! command -v npm >/dev/null 2>&1; then
  echo "" >&2
  echo "ERRORE: npm non trovato (Node non installato o non nel PATH)." >&2
  echo "" >&2
  echo "Su un server di produzione senza Node, usa:" >&2
  echo "  $0 --skip-frontend-build" >&2
  echo "e popola react_build come sopra, oppure installa Node 20+ (es. NodeSource) e rilancia." >&2
  echo "" >&2
  exit 1
else
  echo "Build frontend..."
  cd "$FRONTEND_DIR"
  if [ -f "package-lock.json" ]; then
    npm ci
  else
    npm install
  fi
  npm run build

  echo "Aggiorno react_build..."
  find "$STACK_DIR/react_build" -mindepth 1 -delete 2>/dev/null || true
  cp -R "$FRONTEND_DIR/dist/." "$STACK_DIR/react_build/"
fi

echo ""
echo "Ambiente Pi-like pronto."
echo "Avvio stack:"
echo "  $ROOT_DIR/scripts/up_wsl_pi_like.sh"
echo "  Riavvio senza rebuild immagini: $ROOT_DIR/scripts/up_wsl_pi_like.sh --no-build"
echo ""
echo "URL:"
echo "  http://127.0.0.1:8080"
