#!/usr/bin/env bash
# Per-boot Cloud Agent KOR35: riconfigura SSH da secret ID_DOCKER.
# Deve terminare (exit 0) — non avviare server in foreground qui.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETUP="${ROOT}/.cursor/cloud/ssh_setup.sh"

echo "[kor35-cloud] start: configurazione SSH..."

if [[ ! -x "${SETUP}" ]]; then
  chmod +x "${SETUP}" 2>/dev/null || true
fi

if [[ -f "${SETUP}" ]]; then
  bash "${SETUP}"
else
  echo "[kor35-cloud] WARN: ${SETUP} mancante — skip SSH setup" >&2
fi

echo "[kor35-cloud] start completato."
