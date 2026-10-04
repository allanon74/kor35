#!/usr/bin/env bash
# Dalla postazione di sviluppo: copia gli script, installa prod e Pi, avvia la galleria.
#
#   ./scripts/mirror_tunnel_pair.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_ssh.sh
source "$SCRIPT_DIR/lib_mirror_ssh.sh"
# shellcheck source=lib_prod_ssh.sh
source "$SCRIPT_DIR/lib_prod_ssh.sh"

cd "$ROOT_DIR"

upload() {
  local target_kind="$1"
  local remote_root="$2"
  # shellcheck disable=SC2016
  tar czf - \
    config/docker/compose.prod.yml \
    config/docker/nginx-docker/nginx_conf/mirror-public.conf.example \
    config/docker/nginx-docker/mirror-offline/mirror-offline.html \
    config/docker/nginx-docker/certs_mirror/.gitkeep \
    config/letsencrypt/deploy-hooks/kor35-prod-mirror-public-nginx.sh \
    config/ssh/kor35-mirror-tunnel.sshd.conf \
    config/systemd/kor35-mirror-tunnel.service \
    config/mirror/mirror-tunnel.env.example \
    scripts/install_prod_mirror_tunnel.sh \
    scripts/install_mirror_tunnel.sh \
    scripts/mirror_tunnel_connect.sh \
    scripts/mirror_tunnel_status.sh \
    | if [ "$target_kind" = "prod" ]; then
        prod_ssh_build_args
        ssh "${PROD_SSH_ARGS[@]}" "$PROD_SSH_EFFECTIVE_TARGET" "cd '${remote_root}' && tar xzf -"
      else
        mirror_ssh_build_args
        ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_EFFECTIVE_TARGET" "cd '${remote_root}' && tar xzf -"
      fi
}

echo "Carico i file sul server prod..."
upload prod /srv/kor35
echo "Carico i file sul mirror Pi..."
upload pi /home/pi/kor35-replica

mirror_ssh_run "cd /home/pi/kor35-replica && sudo ./scripts/install_mirror_tunnel.sh --no-start"
mirror_ssh_build_args
ssh "${MIRROR_SSH_ARGS[@]}" "$MIRROR_SSH_EFFECTIVE_TARGET" \
  "sudo cat /etc/kor35/mirror-tunnel/id_ed25519.pub" > /tmp/kor35-mirror-tunnel.pub
chmod 600 /tmp/kor35-mirror-tunnel.pub

prod_ssh_build_args
scp "${PROD_SSH_ARGS[@]}" /tmp/kor35-mirror-tunnel.pub "${PROD_SSH_EFFECTIVE_TARGET}:/tmp/kor35-mirror-tunnel.pub"
prod_ssh_run "sudo /srv/kor35/scripts/install_prod_mirror_tunnel.sh --pubkey-file /tmp/kor35-mirror-tunnel.pub && rm -f /tmp/kor35-mirror-tunnel.pub"
rm -f /tmp/kor35-mirror-tunnel.pub

mirror_ssh_run "sudo systemctl restart kor35-mirror-tunnel.service && sleep 2 && systemctl is-active kor35-mirror-tunnel.service && sudo /home/pi/kor35-replica/scripts/mirror_tunnel_status.sh"
prod_ssh_run "sudo MIRROR_TUNNEL_STATUS_ROLE=prod /srv/kor35/scripts/mirror_tunnel_status.sh"

echo ""
echo "Galleria avviata. DNS ancora da creare su Hetzner se mirror.kor35.it non risolve:"
echo "  A     mirror   (stesso IPv4 di www.kor35.it)"
echo "  AAAA  mirror   (stesso IPv6 di www.kor35.it)"
echo "Poi, sul prod: sudo make install-prod-mirror-tunnel ENV=prod"
