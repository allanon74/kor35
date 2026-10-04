#!/usr/bin/env bash
set -euo pipefail

# Sul server di produzione: utente SSH della galleria, ponte verso Docker,
# vhost mirror.kor35.it e pagina «mirror non raggiungibile».
#
# www.kor35.it non cambia server_name.
#
# Uso (root, sul server):
#   sudo ./scripts/install_prod_mirror_tunnel.sh
#   sudo ./scripts/install_prod_mirror_tunnel.sh --pubkey-file /tmp/mirror-tunnel.pub

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PUBKEY_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --pubkey-file)
      PUBKEY_FILE="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "Eseguire come root (sudo)." >&2
  exit 1
fi

REPO_PATH="${KOR35_REPO_PATH:-$ROOT_DIR}"
DOCKER_DIR="${REPO_PATH}/config/docker"
NGINX_DIR="${DOCKER_DIR}/nginx-docker"
CERT_DEST="${NGINX_DIR}/certs_mirror"
OFFLINE_DIR="${NGINX_DIR}/mirror-offline"
CONF_EXAMPLE="${NGINX_DIR}/nginx_conf/mirror-public.conf.example"
CONF_DEST="${NGINX_DIR}/nginx_conf/mirror-public.conf"
RUN_USER="${KOR35_PROD_TLS_USER:-deploy}"
TUNNEL_USER="kor35-tunnel"
TUNNEL_HOME="/var/lib/kor35-tunnel"
REMOTE_PORT="18443"
DOMAIN="mirror.kor35.it"

if ! grep -q 'certs_mirror' "${DOCKER_DIR}/compose.prod.yml"; then
  echo "compose.prod.yml non monta certs_mirror. Aggiorna il monorepo prima di installare." >&2
  exit 1
fi

if ! command -v socat >/dev/null 2>&1; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y socat
fi

if ! id "$TUNNEL_USER" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "$TUNNEL_HOME" --shell /bin/bash "$TUNNEL_USER"
fi
passwd -l "$TUNNEL_USER" >/dev/null 2>&1 || true
install -d -m 0755 "$TUNNEL_HOME"
install -d -m 0700 -o "$TUNNEL_USER" -g "$TUNNEL_USER" "${TUNNEL_HOME}/.ssh"

if [ -n "$PUBKEY_FILE" ]; then
  if [ ! -f "$PUBKEY_FILE" ]; then
    echo "Chiave pubblica assente: ${PUBKEY_FILE}" >&2
    exit 1
  fi
  read -r key_type key_data _ < "$PUBKEY_FILE"
  if [ -z "${key_type:-}" ] || [ -z "${key_data:-}" ]; then
    echo "Chiave pubblica non valida in ${PUBKEY_FILE}" >&2
    exit 1
  fi
  auth="${TUNNEL_HOME}/.ssh/authorized_keys"
  touch "$auth"
  grep -v 'kor35-mirror-tunnel' "$auth" > "${auth}.tmp" || true
  printf 'command="/bin/sleep infinity",restrict,port-forwarding,permitlisten="127.0.0.1:%s" %s %s kor35-mirror-tunnel\n' \
    "$REMOTE_PORT" "$key_type" "$key_data" >> "${auth}.tmp"
  mv "${auth}.tmp" "$auth"
  chown "$TUNNEL_USER:$TUNNEL_USER" "$auth"
  chmod 600 "$auth"
  echo "Chiave pubblica installata per ${TUNNEL_USER}."
fi

install -m 0644 \
  "${ROOT_DIR}/config/ssh/kor35-mirror-tunnel.sshd.conf" \
  /etc/ssh/sshd_config.d/60-kor35-mirror-tunnel.conf
sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd

GATEWAY=""
if docker inspect kor35_prod_frontend >/dev/null 2>&1; then
  GATEWAY="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{println $v.Gateway}}{{end}}' kor35_prod_frontend | head -n 1 | tr -d '[:space:]')"
fi
if [ -z "$GATEWAY" ]; then
  GATEWAY="172.18.0.1"
  echo "ATTENZIONE: frontend non ispezionabile, uso il bridge ${GATEWAY}." >&2
fi

cat > /etc/systemd/system/kor35-prod-mirror-tunnel-bridge.service <<EOF
[Unit]
Description=KOR35 Prod - ponte galleria mirror (Docker bridge → sshd locale)
After=docker.service network-online.target
Wants=docker.service

[Service]
Type=simple
ExecStart=/usr/bin/socat TCP-LISTEN:${REMOTE_PORT},bind=${GATEWAY},reuseaddr,fork,keepalive TCP:127.0.0.1:${REMOTE_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now kor35-prod-mirror-tunnel-bridge.service

SUBNET="${GATEWAY%.*}.0/16"
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q 'Status: active'; then
  if ! ufw status | grep -q "${REMOTE_PORT}"; then
    ufw allow from "$SUBNET" to any port "$REMOTE_PORT" proto tcp comment 'KOR35 mirror tunnel bridge'
  fi
fi

install -d -m 0750 -o "$RUN_USER" -g "$RUN_USER" "$CERT_DEST"
install -d -m 0755 "$OFFLINE_DIR"
install -m 0644 "${ROOT_DIR}/config/docker/nginx-docker/mirror-offline/mirror-offline.html" \
  "${OFFLINE_DIR}/mirror-offline.html"

if [ ! -s "${CERT_DEST}/fullchain.pem" ] || [ ! -s "${CERT_DEST}/privkey.pem" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 30 \
    -keyout "${CERT_DEST}/privkey.pem" \
    -out "${CERT_DEST}/fullchain.pem" \
    -subj "/CN=${DOMAIN}" >/dev/null 2>&1
  chown "$RUN_USER:$RUN_USER" "${CERT_DEST}/fullchain.pem" "${CERT_DEST}/privkey.pem"
  chmod 644 "${CERT_DEST}/fullchain.pem"
  chmod 600 "${CERT_DEST}/privkey.pem"
  echo "Certificato temporaneo self-signed per ${DOMAIN} (vale finché Let's Encrypt non è pronto)."
fi

install -m 0755 \
  "${ROOT_DIR}/config/letsencrypt/deploy-hooks/kor35-prod-mirror-public-nginx.sh" \
  /etc/letsencrypt/renewal-hooks/deploy/kor35-prod-mirror-public-nginx.sh

sed "s|@MIRROR_TUNNEL_UPSTREAM@|${GATEWAY}:${REMOTE_PORT}|g" "$CONF_EXAMPLE" > "$CONF_DEST"
chmod 644 "$CONF_DEST"

echo "Controllo configurazione nginx prima di ricreare il frontend..."
docker run --rm --entrypoint nginx \
  -v "${NGINX_DIR}/nginx_conf:/etc/nginx/conf.d:ro" \
  -v "${NGINX_DIR}/certs:/etc/nginx/certs:ro" \
  -v "${CERT_DEST}:/etc/nginx/certs_mirror:ro" \
  -v "${OFFLINE_DIR}:/usr/share/nginx/mirror-offline:ro" \
  -v "${NGINX_DIR}/certbot_webroot:/var/www/certbot:ro" \
  nginx:alpine -t

(
  cd "$DOCKER_DIR"
  COMPOSE_PROJECT_NAME=kor35-prod \
    KOR35_BACKEND_ENV_FILE="${REPO_PATH}/backend/.env.prod" \
    docker compose -f compose.base.yml -f compose.prod.yml up -d frontend
)

health_ok=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if curl -fsS --max-time 5 https://www.kor35.it/api/healthz/ >/dev/null; then
    health_ok=1
    break
  fi
  sleep 2
done
if [ "$health_ok" != "1" ]; then
  echo "ERRORE: www.kor35.it/api/healthz/ non risponde dopo il reload del frontend." >&2
  docker logs kor35_prod_frontend --tail 80 >&2 || true
  exit 1
fi

pub_ip="$(curl -4 -fsS --max-time 8 https://api.ipify.org || true)"
dns_ip="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '{print $1; exit}' || true)"
if [ -n "$pub_ip" ] && [ "$dns_ip" = "$pub_ip" ] && command -v certbot >/dev/null 2>&1; then
  echo "DNS ${DOMAIN} → ${dns_ip}. Richiedo il certificato Let's Encrypt."
  if certbot certonly --webroot \
    -w "${NGINX_DIR}/certbot_webroot" \
    -d "$DOMAIN" \
    --non-interactive --agree-tos --keep-until-expiring; then
    KOR35_REPO_PATH="$REPO_PATH" \
      /etc/letsencrypt/renewal-hooks/deploy/kor35-prod-mirror-public-nginx.sh
  else
    echo "ATTENZIONE: certbot non ha emesso ${DOMAIN}. Resta il certificato temporaneo." >&2
  fi
else
  echo "ATTENZIONE: ${DOMAIN} non punta ancora a questo server (DNS=${dns_ip:-nessuno}, pubblico=${pub_ip:-?})." >&2
  echo "Su Hetzner DNS, zona kor35.it:" >&2
  echo "  A     mirror  ${pub_ip:-<IP di www.kor35.it>}" >&2
  echo "  AAAA  mirror  <lo stesso AAAA di www.kor35.it>" >&2
  echo "Poi rilancia questo script per Let's Encrypt." >&2
fi

echo ""
echo "Galleria prod pronta. www.kor35.it risponde."
echo "Upstream nginx: https://${GATEWAY}:${REMOTE_PORT}"
echo "Porta sshd (solo localhost): 127.0.0.1:${REMOTE_PORT}"
if [ ! -s "${TUNNEL_HOME}/.ssh/authorized_keys" ]; then
  echo "Manca ancora la chiave pubblica del Pi (--pubkey-file)."
fi
