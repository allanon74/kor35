#!/usr/bin/env bash
# Post-hook certbot (prod): riavvia nginx Docker anche dopo dry-run o renew fallito.
set -euo pipefail

REPO_PATH="${KOR35_REPO_PATH:-/srv/kor35}"
DOCKER_DIR="${REPO_PATH}/config/docker"

(
  cd "$DOCKER_DIR"
  env COMPOSE_PROJECT_NAME=kor35-prod \
    KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.prod" \
    docker compose -f compose.base.yml -f compose.prod.yml up -d frontend
)
