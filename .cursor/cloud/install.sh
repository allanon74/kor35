#!/usr/bin/env bash
# Bootstrap idempotente Cloud Agent KOR35 (pacchetti + script eseguibili).
# Non avvia servizi lunghi; non richiede Docker locale (ops via SSH mirror/prod).
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

ensure_pkg openssh-client
# Opzionale: proxy HTTP CONNECT (reti aziendali); ignore se apt fallisce
if ! dpkg -s corkscrew >/dev/null 2>&1; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq || true
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq corkscrew || \
    echo "[kor35-cloud] WARN: corkscrew non installato (non bloccante)" >&2
fi

# Locale usata da alcuni host remoti / shell
if ! locale -a 2>/dev/null | grep -qi 'en_US.utf8\|en_US.UTF-8'; then
  sudo locale-gen en_US.UTF-8 >/dev/null 2>&1 || true
fi

chmod +x "${ROOT}/.cursor/cloud/"*.sh 2>/dev/null || true

# Verifica presenza secret (non stampare contenuto)
if [[ -n "${ID_DOCKER:-}" ]]; then
  echo "[kor35-cloud] secret ID_DOCKER: presente"
else
  echo "[kor35-cloud] WARN: secret ID_DOCKER assente — aggiungilo nell'Environment Cursor" >&2
fi

echo "[kor35-cloud] install completato."
