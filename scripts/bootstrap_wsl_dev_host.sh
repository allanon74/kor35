#!/usr/bin/env bash
set -euo pipefail

# Bootstrap host WSL Ubuntu per ambiente KOR35 (Docker-first).
# Installa prerequisiti macchina: git, make, docker engine + compose plugin,
# utilita' base e (opzionale) Node.js LTS.

INSTALL_NODE=true
INSTALL_GH=false
USERNAME_HINT="${SUDO_USER:-$USER}"

usage() {
  cat <<'EOF'
Uso: bootstrap_wsl_dev_host.sh [opzioni]

Opzioni:
  --skip-node          Non installare Node.js/npm (utile se non fai build frontend locale)
  --install-gh         Installa GitHub CLI (gh)
  --user <nome>        Utente da aggiungere al gruppo docker (default: utente che invoca sudo)
  -h, --help           Mostra questo help

Esempi:
  sudo ./scripts/bootstrap_wsl_dev_host.sh
  sudo ./scripts/bootstrap_wsl_dev_host.sh --skip-node
  sudo ./scripts/bootstrap_wsl_dev_host.sh --install-gh --user django
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-node)
      INSTALL_NODE=false
      shift
      ;;
    --install-gh)
      INSTALL_GH=true
      shift
      ;;
    --user)
      USERNAME_HINT="${2:-}"
      if [ -z "$USERNAME_HINT" ]; then
        echo "--user richiede un valore" >&2
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root (es. sudo ./scripts/bootstrap_wsl_dev_host.sh)." >&2
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Sistema non supportato: serve apt-get (Ubuntu/Debian)." >&2
  exit 1
fi

echo "==> Aggiorno indice pacchetti APT"
apt-get update

echo "==> Installo pacchetti base"
apt-get install -y \
  ca-certificates \
  curl \
  gnupg \
  lsb-release \
  git \
  make \
  rsync \
  openssh-client \
  jq \
  unzip \
  python3 \
  python3-pip \
  python3-venv

echo "==> Configuro repository Docker ufficiale"
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi
chmod a+r /etc/apt/keyrings/docker.gpg

ARCH="$(dpkg --print-architecture)"
CODENAME="$(
  . /etc/os-release
  echo "${VERSION_CODENAME:-}"
)"
if [ -z "$CODENAME" ]; then
  echo "Impossibile determinare VERSION_CODENAME da /etc/os-release" >&2
  exit 1
fi

cat >/etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$ARCH signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $CODENAME stable
EOF

echo "==> Installo Docker Engine + Compose plugin"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if id "$USERNAME_HINT" >/dev/null 2>&1; then
  echo "==> Aggiungo utente '$USERNAME_HINT' al gruppo docker"
  usermod -aG docker "$USERNAME_HINT" || true
else
  echo "Utente '$USERNAME_HINT' non trovato: salto usermod -aG docker."
fi

if [ "$INSTALL_NODE" = true ]; then
  echo "==> Installo Node.js LTS (NodeSource 22.x)"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
else
  echo "==> Node.js saltato (--skip-node)"
fi

if [ "$INSTALL_GH" = true ]; then
  echo "==> Installo GitHub CLI (gh)"
  if [ ! -f /etc/apt/keyrings/githubcli-archive-keyring.gpg ]; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/etc/apt/keyrings/githubcli-archive-keyring.gpg
    chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    >/etc/apt/sources.list.d/github-cli.list
  apt-get update
  apt-get install -y gh
fi

echo ""
echo "Bootstrap host completato."
echo "Verifiche consigliate (come utente normale, in nuova shell):"
echo "  docker --version"
echo "  docker compose version"
echo "  make --version"
if [ "$INSTALL_NODE" = true ]; then
  echo "  node --version && npm --version"
fi
echo ""
echo "Nota: dopo il cambio gruppo docker fai logout/login WSL (o 'newgrp docker')."
