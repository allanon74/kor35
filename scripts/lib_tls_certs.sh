#!/usr/bin/env bash
# Funzioni condivise per deploy certificati TLS (prod + mirror).
set -euo pipefail

tls_verify_certs_dir() {
  local dir="$1"
  local label="${2:-}"
  if [ ! -f "${dir}/fullchain.pem" ] || [ ! -f "${dir}/privkey.pem" ]; then
    echo "Certificati mancanti in ${dir}/ (${label})." >&2
    return 1
  fi
  return 0
}

tls_copy_le_live_to_dir() {
  local live_dir="$1"
  local dest_dir="$2"
  local owner="${3:-}"

  tls_verify_certs_dir "$live_dir" "letsencrypt live"

  mkdir -p "$dest_dir"
  install -m 0644 "${live_dir}/fullchain.pem" "${dest_dir}/fullchain.pem"
  install -m 0600 "${live_dir}/privkey.pem" "${dest_dir}/privkey.pem"

  if [ -n "$owner" ]; then
    chown "$owner" "${dest_dir}/fullchain.pem" "${dest_dir}/privkey.pem"
  fi
}

tls_reload_frontend_nginx() {
  local docker_dir="$1"
  local compose_project_name="${2:-}"
  local backend_env_file="${3:-}"

  local -a env_args=()
  if [ -n "$compose_project_name" ]; then
    env_args+=(COMPOSE_PROJECT_NAME="$compose_project_name")
  fi
  if [ -n "$backend_env_file" ]; then
    env_args+=(KOR35_BACKEND_ENV_FILE="$backend_env_file")
  fi

  (
    cd "$docker_dir"
    if [ "${#env_args[@]}" -gt 0 ]; then
      env "${env_args[@]}" docker compose -f compose.base.yml -f "compose.${KOR35_TLS_COMPOSE_ENV:-mirror}.yml" \
        exec -T frontend nginx -s reload
    else
      docker compose -f compose.base.yml -f "compose.${KOR35_TLS_COMPOSE_ENV:-mirror}.yml" \
        exec -T frontend nginx -s reload
    fi
  )
}

tls_cert_days_until_expiry() {
  local cert_file="$1"
  openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null \
    | sed 's/notAfter=//' \
    | xargs -I{} date -d "{}" +%s 2>/dev/null \
    | awk -v now="$(date +%s)" '{ print int(($1 - now) / 86400) }'
}

tls_install_deploy_hook() {
  local src_hook="$1"
  local hook_name="$2"
  local hook_phase="${3:-deploy}"

  if [ "$(id -u)" -ne 0 ]; then
    echo "tls_install_deploy_hook richiede root." >&2
    return 1
  fi

  local dest_dir="/etc/letsencrypt/renewal-hooks/${hook_phase}"
  mkdir -p "$dest_dir"
  install -m 0755 "$src_hook" "${dest_dir}/${hook_name}"
}
