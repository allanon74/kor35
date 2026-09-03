#!/usr/bin/env bash
# Avvio per-boot dello stack KOR35 dev-home: (ri)avvia il daemon Docker e porta
# su i container. Le immagini sono già state costruite in fase di install.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

"$ROOT/.cursor/cloud/dockerd-up.sh"

export KOR35_BACKEND_ENV_FILE="$ROOT/backend/.env.dev-home"
cd config/docker

# --build come rete di sicurezza se un'immagine mancasse (es. avvio JIT senza
# snapshot). Con le immagini già presenti la cache rende l'operazione rapida.
docker compose -f compose.base.yml -f compose.dev-home.yml up -d --build

docker compose -f compose.base.yml -f compose.dev-home.yml ps
echo "Stack KOR35 dev-home avviato su http://localhost:8080"
