#!/usr/bin/env bash
# Controlla che il vhost mirror.kor35.it sia accettato da nginx, senza toccare la produzione.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NGINX_SRC="${ROOT}/config/docker/nginx-docker"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/conf" "$TMP/certs" "$TMP/certs_mirror" "$TMP/offline" "$TMP/webroot/.well-known/acme-challenge"

openssl req -x509 -nodes -newkey rsa:2048 -days 2 \
  -keyout "$TMP/certs/privkey.pem" \
  -out "$TMP/certs/fullchain.pem" \
  -subj "/CN=www.kor35.it" >/dev/null 2>&1
openssl req -x509 -nodes -newkey rsa:2048 -days 2 \
  -keyout "$TMP/certs_mirror/privkey.pem" \
  -out "$TMP/certs_mirror/fullchain.pem" \
  -subj "/CN=mirror.kor35.it" >/dev/null 2>&1

cp "${NGINX_SRC}/nginx_conf/default.conf" "$TMP/conf/default.conf"
cp "${NGINX_SRC}/nginx_conf/ssl_params.snippets" "$TMP/conf/ssl_params.snippets"
cp "${NGINX_SRC}/nginx_conf/common_locations.snippets" "$TMP/conf/common_locations.snippets"
sed 's|@MIRROR_TUNNEL_UPSTREAM@|127.0.0.1:9|g' \
  "${NGINX_SRC}/nginx_conf/mirror-public.conf.example" > "$TMP/conf/mirror-public.conf"
cp "${NGINX_SRC}/mirror-offline/mirror-offline.html" "$TMP/offline/mirror-offline.html"

grep -q 'Il server di mirror non è raggiungibile.' "$TMP/offline/mirror-offline.html"
grep -q 'server_name mirror.kor35.it;' "$TMP/conf/mirror-public.conf"
grep -q 'error_page 502 503 504 =200 /mirror-offline.html;' "$TMP/conf/mirror-public.conf"
grep -q 'server_name www.kor35.it www.k-o-r-35.it;' "$TMP/conf/default.conf"
if grep -q 'proxy_intercept_errors on' "$TMP/conf/mirror-public.conf"; then
  echo "proxy_intercept_errors on nasconderebbe i 502 del Pi" >&2
  exit 1
fi

docker run --rm --entrypoint nginx \
  -v "$TMP/conf:/etc/nginx/conf.d:ro" \
  -v "$TMP/certs:/etc/nginx/certs:ro" \
  -v "$TMP/certs_mirror:/etc/nginx/certs_mirror:ro" \
  -v "$TMP/offline:/usr/share/nginx/mirror-offline:ro" \
  -v "$TMP/webroot:/var/www/certbot:ro" \
  nginx:alpine -t

# Upstream 127.0.0.1:9 non ascolta: la pagina di disclaimer deve uscire con HTTP 200.
NAME="kor35-nginx-offline-test-$$"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" \
  -v "$TMP/conf:/etc/nginx/conf.d:ro" \
  -v "$TMP/certs:/etc/nginx/certs:ro" \
  -v "$TMP/certs_mirror:/etc/nginx/certs_mirror:ro" \
  -v "$TMP/offline:/usr/share/nginx/mirror-offline:ro" \
  -v "$TMP/webroot:/var/www/certbot:ro" \
  nginx:alpine >/dev/null
cleanup_nginx() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap 'cleanup_nginx; rm -rf "$TMP"' EXIT

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if docker exec "$NAME" wget -q -O /dev/null --no-check-certificate --header='Host: mirror.kor35.it' https://127.0.0.1/ 2>/dev/null; then
    break
  fi
  sleep 0.2
done

BODY="$(docker run --rm --network "container:${NAME}" curlimages/curl:8.10.1 \
  -k -sS --resolve mirror.kor35.it:443:127.0.0.1 https://mirror.kor35.it/ \
  -w '\n%{http_code}')"
CODE="$(printf '%s' "$BODY" | tail -n 1)"
HTML="$(printf '%s' "$BODY" | sed '$d')"
printf '%s' "$HTML" | grep -q 'Il server di mirror non è raggiungibile.'
if [ "$CODE" != "200" ]; then
  echo "atteso HTTP 200 sulla pagina offline, ricevuto ${CODE}" >&2
  exit 1
fi

echo "OK test_mirror_tunnel_nginx"
