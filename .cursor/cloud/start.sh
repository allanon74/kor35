#!/usr/bin/env bash
# Per-boot Cloud Agent KOR35: avvia dockerd + riconfigura SSH da secret ID_DOCKER.
# Deve terminare (exit 0) — non tenere server in foreground.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SETUP="${ROOT}/.cursor/cloud/ssh_setup.sh"

echo "[kor35-cloud] start: bootstrap runtime..."

ensure_docker_socket_access() {
  if [[ ! -S /var/run/docker.sock ]]; then
    return 0
  fi
  sudo groupadd -f docker >/dev/null 2>&1 || true
  sudo usermod -aG docker "$(id -un)" >/dev/null 2>&1 || true
  sudo chgrp docker /var/run/docker.sock >/dev/null 2>&1 || true
  sudo chmod g+rw /var/run/docker.sock >/dev/null 2>&1 || true
  if command -v setfacl >/dev/null 2>&1; then
    sudo setfacl -m "u:$(id -un):rw" /var/run/docker.sock >/dev/null 2>&1 || true
  fi
}

start_docker_daemon() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "[kor35-cloud] WARN: docker CLI assente — skip avvio daemon" >&2
    return 0
  fi

  ensure_docker_socket_access

  if docker info >/dev/null 2>&1; then
    echo "[kor35-cloud] Docker già in esecuzione"
    docker compose version >/dev/null 2>&1 || true
    return 0
  fi

  echo "[kor35-cloud] avvio Docker daemon..."
  if command -v service >/dev/null 2>&1; then
    sudo sh -c 'service docker start >/tmp/docker-service-start.log 2>&1' || \
      echo "[kor35-cloud] WARN: service docker start fallito, provo dockerd diretto" >&2
  fi

  if ! pgrep -x dockerd >/dev/null 2>&1; then
    sudo sh -c 'nohup dockerd --host=unix:///var/run/docker.sock >/tmp/dockerd.log 2>&1 &'
  fi

  local i
  for i in $(seq 1 60); do
    ensure_docker_socket_access
    if docker info >/dev/null 2>&1; then
      echo "[kor35-cloud] Docker pronto ($(docker --version))"
      docker compose version 2>/dev/null || true
      return 0
    fi
    sleep 1
  done

  echo "[kor35-cloud] ERROR: Docker non pronto entro 60s" >&2
  [[ -f /tmp/docker-service-start.log ]] && tail -n 40 /tmp/docker-service-start.log >&2 || true
  [[ -f /tmp/dockerd.log ]] && tail -n 60 /tmp/dockerd.log >&2 || true
  return 1
}

# Docker prima (i test KOR35 sono Docker-first)
start_docker_daemon || true

# SSH mirror/prod (best-effort)
if [[ ! -x "${SETUP}" ]]; then
  chmod +x "${SETUP}" 2>/dev/null || true
fi
if [[ -f "${SETUP}" ]]; then
  bash "${SETUP}" || echo "[kor35-cloud] WARN: ssh_setup fallito (non bloccante)" >&2
else
  echo "[kor35-cloud] WARN: ${SETUP} mancante — skip SSH setup" >&2
fi

echo "[kor35-cloud] start completato."
