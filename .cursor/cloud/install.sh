#!/usr/bin/env bash
# Bootstrap idempotente Cloud Agent KOR35 (Build / install).
# Docker CE è nell'immagine (.cursor/Dockerfile); qui si verificano tool e secrets.
# Non avvia daemon lunghi (docker → start.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT}"

echo "[kor35-cloud] install: root=${ROOT}"

ensure_pkg() {
  local pkg="$1"
  if dpkg -s "${pkg}" >/dev/null 2>&1; then
    echo "[kor35-cloud] pacchetto già presente: ${pkg}"
    return 0
  fi
  echo "[kor35-cloud] installo ${pkg}..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${pkg}"
}

# Tool leggeri anche se l'immagine base non è il Dockerfile DinD
ensure_pkg openssh-client
ensure_pkg make
ensure_pkg python3
if ! dpkg -s corkscrew >/dev/null 2>&1; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq || true
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq corkscrew || \
    echo "[kor35-cloud] WARN: corkscrew non installato (non bloccante)" >&2
fi

if ! locale -a 2>/dev/null | grep -qi 'en_US.utf8\|en_US.UTF-8'; then
  sudo locale-gen en_US.UTF-8 >/dev/null 2>&1 || true
fi

chmod +x "${ROOT}/.cursor/cloud/"*.sh 2>/dev/null || true

if command -v docker >/dev/null 2>&1; then
  echo "[kor35-cloud] docker CLI: $(docker --version)"
  docker compose version >/dev/null 2>&1 && \
    echo "[kor35-cloud] docker compose: $(docker compose version)" || \
    echo "[kor35-cloud] WARN: docker compose plugin assente" >&2
else
  echo "[kor35-cloud] WARN: docker CLI assente — serve Build da .cursor/Dockerfile" >&2
fi

# Verifica presence secret (non stampare contenuto)
if [[ -n "${ID_DOCKER:-}" ]]; then
  echo "[kor35-cloud] secret ID_DOCKER: presente"
else
  echo "[kor35-cloud] WARN: secret ID_DOCKER assente — SSH mirror/prod non disponibile" >&2
fi

if [[ -n "${SECRET_KEY:-}" ]]; then
  echo "[kor35-cloud] secret SECRET_KEY: presente"
else
  echo "[kor35-cloud] WARN: secret SECRET_KEY assente — useremo placeholder in .env.dev-home" >&2
fi

# Materializza backend/.env.dev-home da template se manca (idempotente)
ENV_FILE="${ROOT}/backend/.env.dev-home"
TEMPLATE="${ROOT}/config/env_templates/backend.dev-home.env.example"
if [[ ! -f "${ENV_FILE}" && -f "${TEMPLATE}" ]]; then
  echo "[kor35-cloud] creo ${ENV_FILE} dal template"
  cp "${TEMPLATE}" "${ENV_FILE}"
  if [[ -n "${SECRET_KEY:-}" ]]; then
    ROOT="${ROOT}" SECRET_KEY="${SECRET_KEY}" python3 - <<'PY'
import os
from pathlib import Path
path = Path(os.environ["ROOT"]) / "backend" / ".env.dev-home"
text = path.read_text()
sk = os.environ["SECRET_KEY"]
text = text.replace("CHANGE_ME_DEV_HOME_SECRET_KEY", sk, 1)
path.write_text(text)
print("[kor35-cloud] SECRET_KEY scritto in backend/.env.dev-home")
PY
  fi
else
  echo "[kor35-cloud] env file: $([[ -f "${ENV_FILE}" ]] && echo presente || echo assente)"
fi

echo "[kor35-cloud] install completato."
