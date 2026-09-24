#!/usr/bin/env bash
# Avvia il daemon Docker dentro il pod del Cloud Agent (Docker-in-Docker).
#
# Accorgimenti per l'ambiente annidato non privilegiato del Cloud Agent:
#   1. storage-driver "fuse-overlayfs": overlay2 su overlayfs non è montabile
#      nel pod; fuse-overlayfs (con /dev/fuse) funziona ed è molto più veloce
#      e leggero di "vfs".
#   2. iptables-legacy: il backend nftables spesso non è utilizzabile nel pod;
#      con le regole legacy il NAT del bridge Docker funziona.
#   3. net.bridge.bridge-nf-call-iptables=0: rete di sicurezza per evitare che
#      il traffico TCP tra container sullo stesso bridge (es. backend -> db)
#      vada in timeout su alcuni kernel.
#
# Idempotente: se il daemon è già attivo si limita a garantire i permessi socket.
set -euo pipefail

# Docker Engine + Compose v2 (se assenti). Su un VM già provisionato (snapshot)
# questo ramo non viene eseguito.
if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2
fi

# fuse-overlayfs + iptables (se assenti).
if ! command -v fuse-overlayfs >/dev/null 2>&1; then
  sudo apt-get update && sudo apt-get install -y fuse-overlayfs iptables || true
fi

# Preferisci iptables-legacy: il NAT del bridge Docker è più affidabile nel pod.
sudo update-alternatives --set iptables /usr/sbin/iptables-legacy >/dev/null 2>&1 || true
sudo update-alternatives --set ip6tables /usr/sbin/ip6tables-legacy >/dev/null 2>&1 || true

sudo mkdir -p /etc/docker
if [ ! -f /etc/docker/daemon.json ] || ! grep -q '"storage-driver"[[:space:]]*:[[:space:]]*"fuse-overlayfs"' /etc/docker/daemon.json; then
  echo '{ "storage-driver": "fuse-overlayfs" }' | sudo tee /etc/docker/daemon.json >/dev/null
fi

if ! docker info >/dev/null 2>&1 && ! sudo docker info >/dev/null 2>&1; then
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
echo "dockerd pronto (storage-driver=fuse-overlayfs)."
