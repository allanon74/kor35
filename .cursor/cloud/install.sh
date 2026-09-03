#!/usr/bin/env bash
# Bootstrap idempotente dello stack di sviluppo KOR35 (profilo dev-home) per
# un Cloud Agent. Docker-first: Postgres + Redis + Django (Gunicorn/Daphne) +
# Nginx che serve la build React, esattamente come su WSL/Pi.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# 1) Docker Engine + Compose v2 (se assenti).
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2
fi

# 2) Avvia il daemon (vfs + fix networking) così da poter buildare le immagini.
"$ROOT/.cursor/cloud/dockerd-up.sh"

# 3) File env backend del profilo dev-home (da template versionato).
[ -f backend/.env.dev-home ] || ./scripts/use_env_backend.sh --env dev-home

# 4) Directory dati montate da Nginx/backend.
mkdir -p \
  config/docker/nginx-docker/static_data \
  config/docker/nginx-docker/media_data \
  config/docker/nginx-docker/react_build \
  config/docker/nginx-docker/react_build_pilot \
  .runtime-state

# 5) Build del frontend React (Vite) e copia in react_build (servito da Nginx).
if [ -d frontend ]; then
  ( cd frontend && (npm ci || npm install) && npm run build )
  find config/docker/nginx-docker/react_build -mindepth 1 -delete 2>/dev/null || true
  cp -R frontend/dist/. config/docker/nginx-docker/react_build/
fi

# 6) Build dell'immagine backend (Postgres/Redis/Nginx sono immagini ufficiali).
export KOR35_BACKEND_ENV_FILE="$ROOT/backend/.env.dev-home"
( cd config/docker && docker compose -f compose.base.yml -f compose.dev-home.yml build backend )

echo "Install completato: immagini pronte, env dev-home creato."
