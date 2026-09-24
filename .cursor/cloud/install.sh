#!/usr/bin/env bash
# Bootstrap idempotente dello stack di sviluppo KOR35 (profilo dev-home) per un
# Cloud Agent. Docker-first: Postgres + Redis + Django (Gunicorn/Daphne) + Nginx
# che serve la build React, esattamente come su WSL/Pi.
#
# Gira dopo il checkout del repo. Deve terminare (nessun processo in foreground).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

# 1) Docker Engine + daemon (fuse-overlayfs + fix networking) così da poter
#    buildare le immagini. Idempotente.
"$ROOT/.cursor/cloud/dockerd-up.sh"

# 2) File env backend del profilo dev-home (da template versionato).
[ -f backend/.env.dev-home ] || ./scripts/use_env_backend.sh --env dev-home

# 3) Directory dati montate da Nginx/backend.
mkdir -p \
  config/docker/nginx-docker/static_data \
  config/docker/nginx-docker/media_data \
  config/docker/nginx-docker/react_build \
  config/docker/nginx-docker/react_build_pilot \
  .runtime-state

# 4) Build del frontend React (Vite) e della console pilota, copia in react_build
#    (servito da Nginx). Non-root: qui l'utente è "ubuntu".
if [ -d frontend ]; then
  ( cd frontend && (npm ci || npm install) && npm run build )
  find config/docker/nginx-docker/react_build -mindepth 1 -delete 2>/dev/null || true
  cp -R frontend/dist/. config/docker/nginx-docker/react_build/
fi
if [ -d frontend-pilot ] && [ -f frontend-pilot/package.json ]; then
  ( cd frontend-pilot && (npm ci || npm install) && npm run build )
  find config/docker/nginx-docker/react_build_pilot -mindepth 1 -delete 2>/dev/null || true
  cp -R frontend-pilot/dist/. config/docker/nginx-docker/react_build_pilot/
fi

# 5) Build dell'immagine backend (Postgres/Redis/Nginx/coturn sono immagini
#    ufficiali). timer_dispatch riusa l'immagine "docker-backend:latest", quindi
#    va costruita prima dell'avvio dello stack.
export KOR35_BACKEND_ENV_FILE="$ROOT/backend/.env.dev-home"
( cd config/docker && docker compose -f compose.base.yml -f compose.dev-home.yml build backend )

echo "Install completato: immagini pronte, env dev-home creato."
