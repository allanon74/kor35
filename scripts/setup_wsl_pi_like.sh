#!/usr/bin/env bash
set -euo pipefail

# Prepara l'ambiente WSL "Pi-like" in conf/nginx-docker:
# - link backend sorgenti
# - build frontend e copia in react_build
# - creazione directory dati (db/static/media)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STACK_DIR="$ROOT_DIR/conf/nginx-docker"
BACKEND_DIR="$ROOT_DIR"
FRONTEND_DIR="/home/django/progetti/kor35-app"

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

if [ -L "$STACK_DIR/backend_src" ] || [ -d "$STACK_DIR/backend_src" ]; then
  rm -rf "$STACK_DIR/backend_src"
fi
ln -s "$BACKEND_DIR" "$STACK_DIR/backend_src"

if [ -f "$BACKEND_DIR/.env.wsl.example" ] && [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.wsl.example" "$BACKEND_DIR/.env"
  echo "Creato $BACKEND_DIR/.env da .env.wsl.example"
fi

echo "Build frontend..."
cd "$FRONTEND_DIR"
if [ -f "package-lock.json" ]; then
  npm ci
else
  npm install
fi
npm run build

echo "Aggiorno react_build..."
rm -rf "$STACK_DIR/react_build"/*
cp -R "$FRONTEND_DIR/dist/." "$STACK_DIR/react_build/"

echo ""
echo "Ambiente Pi-like pronto."
echo "Avvio stack:"
echo "  $ROOT_DIR/scripts/up_wsl_pi_like.sh"
echo "  Riavvio senza rebuild immagini: $ROOT_DIR/scripts/up_wsl_pi_like.sh --no-build"
echo ""
echo "URL:"
echo "  http://127.0.0.1:8080"
