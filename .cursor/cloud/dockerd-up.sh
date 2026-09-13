#!/usr/bin/env bash
# Avvia il daemon Docker dentro il pod del Cloud Agent (Docker-in-Docker).
#
# Due accorgimenti indispensabili in questo ambiente annidato:
#   1. storage-driver "vfs": overlayfs-su-overlayfs non è montabile nel pod.
#   2. net.bridge.bridge-nf-call-iptables=0: senza questo il traffico TCP tra
#      container sullo stesso bridge (es. backend -> db) va in timeout.
#
# Idempotente: se il daemon è già attivo non fa nulla.
set -euo pipefail

sudo mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ] || ! grep -q '"storage-driver"[[:space:]]*:[[:space:]]*"vfs"' /etc/docker/daemon.json; then
  echo '{ "storage-driver": "vfs" }' | sudo tee /etc/docker/daemon.json >/dev/null
fi

if ! sudo docker info >/dev/null 2>&1; then
  sudo bash -c 'nohup dockerd >/var/log/dockerd.log 2>&1 &'
  for _ in $(seq 1 60); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi

# Da eseguire dopo l'avvio del daemon: il modulo br_netfilter e la sysctl
# esistono solo quando esiste almeno un bridge Docker.
sudo modprobe br_netfilter >/dev/null 2>&1 || true
sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || true
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null 2>&1 || true

# Rende la socket usabile senza sudo (docker compose gira come utente ubuntu).
sudo chmod 666 /var/run/docker.sock 2>/dev/null || true

sudo docker info >/dev/null 2>&1
echo "dockerd pronto (storage-driver=vfs)."
