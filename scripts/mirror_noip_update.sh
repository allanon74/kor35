#!/usr/bin/env bash
# Aggiorna l'hostname No-IP del mirror (default kor35.ddns.net) con l'IP pubblico
# visto dal Raspberry. Così il nome segue il Pi se cambia router.
#
# Credenziali: /etc/kor35/noip.env (mai nel git). Vedi config/mirror/noip.env.example.
#
# Uso sul Pi:
#   sudo ./scripts/mirror_noip_update.sh
#   sudo ./scripts/mirror_noip_update.sh --force
#   sudo ./scripts/mirror_noip_update.sh --dry-run
#   sudo ./scripts/mirror_noip_update.sh --status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

NOIP_USER_AGENT="${NOIP_USER_AGENT:-KOR35 MirrorNoIP/linux-1.0 maintainer-mirror@kor35.it}"
NOIP_UPDATE_URL="${NOIP_UPDATE_URL:-https://dynupdate.no-ip.com/nic/update}"

# Codici che richiedono un intervento (password, hostname, User-Agent). Non ritentare
# a ogni timer finché /etc/kor35/noip.env non cambia, oppure con --force.
noip_response_is_fatal() {
  case "$1" in
    badauth|badagent|nohost|abuse|!donator) return 0 ;;
    *) return 1 ;;
  esac
}

noip_classify_response() {
  local line
  line="$(printf '%s\n' "$1" | head -n 1 | tr -d '\r')"
  line="${line%% *}"
  printf '%s' "$line"
}

noip_ipv4_valid() {
  local ip="$1" o1 o2 o3 o4
  [[ "$ip" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]] || return 1
  IFS=. read -r o1 o2 o3 o4 <<<"$ip"
  local o
  for o in "$o1" "$o2" "$o3" "$o4"; do
    [ "$((10#$o))" -le 255 ] || return 1
  done
}

noip_ipv4_is_cgnat() {
  local o1 o2
  noip_ipv4_valid "$1" || return 1
  IFS=. read -r o1 o2 _ _ <<<"$1"
  [ "$((10#$o1))" -eq 100 ] || return 1
  local n=$((10#$o2))
  [ "$n" -ge 64 ] && [ "$n" -le 127 ]
}

# Indirizzi che non vanno pubblicati su DNS (LAN, loopback, CGNAT, multicast).
noip_ipv4_is_nonglobal() {
  local o1 o2
  noip_ipv4_valid "$1" || return 0
  IFS=. read -r o1 o2 _ _ <<<"$1"
  o1=$((10#$o1))
  o2=$((10#$o2))
  [ "$o1" -eq 0 ] && return 0
  [ "$o1" -eq 10 ] && return 0
  [ "$o1" -eq 127 ] && return 0
  [ "$o1" -eq 169 ] && [ "$o2" -eq 254 ] && return 0
  [ "$o1" -eq 172 ] && [ "$o2" -ge 16 ] && [ "$o2" -le 31 ] && return 0
  [ "$o1" -eq 192 ] && [ "$o2" -eq 168 ] && return 0
  [ "$o1" -ge 224 ] && return 0
  noip_ipv4_is_cgnat "$1" && return 0
  return 1
}

noip_ipv4_is_global() {
  noip_ipv4_valid "$1" || return 1
  noip_ipv4_is_nonglobal "$1" && return 1
  return 0
}

# Stampa yes oppure no.
noip_should_update() {
  local last_ip="$1" last_epoch="$2" now_epoch="$3" current_ip="$4" force="$5" refresh_sec="$6"
  if [ "$force" = "1" ]; then
    printf '%s' yes
    return 0
  fi
  if [ -z "$last_ip" ] || [ "$last_ip" != "$current_ip" ]; then
    printf '%s' yes
    return 0
  fi
  local last="${last_epoch:-0}"
  if [ "$((now_epoch - last))" -ge "$refresh_sec" ]; then
    printf '%s' yes
    return 0
  fi
  printf '%s' no
}

noip_curl_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

noip_credentials_ready() {
  [ -n "${NOIP_USERNAME:-}" ] || return 1
  [ -n "${NOIP_PASSWORD:-}" ] || return 1
  case "$NOIP_USERNAME" in
    CHANGE_ME*|your-email*) return 1 ;;
  esac
  case "$NOIP_PASSWORD" in
    CHANGE_ME*|your-password*) return 1 ;;
  esac
  return 0
}

noip_hostname_valid() {
  [[ "${1:-}" =~ ^[A-Za-z0-9.-]+$ ]]
}

noip_default_src_ip() {
  if [ "${NOIP_ASSUME_OFFLINE:-0}" = "1" ]; then
    return 1
  fi
  if [ -n "${NOIP_SRC_IP_OVERRIDE:-}" ]; then
    printf '%s\n' "$NOIP_SRC_IP_OVERRIDE"
    return 0
  fi
  ip -4 route get 1.1.1.1 2>/dev/null \
    | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}'
}

noip_detect_public_ipv4() {
  if [ -n "${NOIP_PUBLIC_IP_OVERRIDE:-}" ]; then
    printf '%s\n' "$NOIP_PUBLIC_IP_OVERRIDE"
    return 0
  fi
  local url ip endpoints=(
    "https://api.ipify.org"
    "https://ifconfig.me/ip"
    "https://icanhazip.com"
    "http://ip1.dynupdate.no-ip.com/"
  )
  for url in "${endpoints[@]}"; do
    ip="$(curl --ipv4 --fail --silent --show-error --max-time 8 \
      -A "$NOIP_USER_AGENT" "$url" 2>/dev/null | tr -d '[:space:]' || true)"
    if noip_ipv4_valid "$ip"; then
      printf '%s\n' "$ip"
      return 0
    fi
  done
  return 1
}

noip_state_value() {
  local key="$1" line
  [ -f "${NOIP_STATE_FILE:-}" ] || return 0
  line="$(grep -E "^${key}=" "$NOIP_STATE_FILE" | tail -n 1 || true)"
  printf '%s' "${line#*=}"
}

noip_write_state() {
  local tmp="${NOIP_STATE_FILE}.tmp.$$"
  umask 077
  cat >"$tmp" <<EOF
hostname=${STATE_HOSTNAME:-}
public_ip=${STATE_PUBLIC_IP:-}
result=${STATE_RESULT:-}
updated_at_epoch=${STATE_UPDATED_EPOCH:-0}
halt_reason=${STATE_HALT_REASON:-}
halt_env_mtime=${STATE_HALT_ENV_MTIME:-0}
upnp=${STATE_UPNP:-}
EOF
  mv "$tmp" "$NOIP_STATE_FILE"
  chmod 600 "$NOIP_STATE_FILE" 2>/dev/null || true
}

noip_env_mtime() {
  if [ -f "${NOIP_ENV_FILE:-}" ]; then
    stat -c %Y "$NOIP_ENV_FILE"
  else
    printf '%s' 0
  fi
}

noip_load_env() {
  NOIP_USERNAME="${NOIP_USERNAME:-}"
  NOIP_PASSWORD="${NOIP_PASSWORD:-}"
  NOIP_HOSTNAME="${NOIP_HOSTNAME:-kor35.ddns.net}"
  NOIP_UPNP="${NOIP_UPNP:-1}"
  NOIP_REFRESH_SEC="${NOIP_REFRESH_SEC:-86400}"
  NOIP_UPNP_TCP_MAPS="${NOIP_UPNP_TCP_MAPS:-80:80 443:443 22:10022}"
  if [ -f "${NOIP_ENV_FILE:-}" ]; then
    # shellcheck disable=SC1090
    source "$NOIP_ENV_FILE"
  fi
  NOIP_HOSTNAME="${NOIP_HOSTNAME:-kor35.ddns.net}"
  NOIP_UPNP="${NOIP_UPNP:-1}"
  NOIP_REFRESH_SEC="${NOIP_REFRESH_SEC:-86400}"
  NOIP_UPNP_TCP_MAPS="${NOIP_UPNP_TCP_MAPS:-80:80 443:443 22:10022}"
}

# Corpo della risposta No-IP su stdout. Imposta NOIP_HTTP_CODE.
noip_http_update() {
  local hostname="$1" ip="$2"
  local cfg err raw body
  cfg="$(mktemp)"
  chmod 600 "$cfg"
  {
    printf 'user = "%s:%s"\n' \
      "$(noip_curl_escape "$NOIP_USERNAME")" \
      "$(noip_curl_escape "$NOIP_PASSWORD")"
    printf 'user-agent = "%s"\n' "$(noip_curl_escape "$NOIP_USER_AGENT")"
    echo "ipv4"
    echo "silent"
    echo "show-error"
    echo "max-time = 20"
  } >"$cfg"
  raw="$(curl --config "$cfg" -w $'\n__HTTP__%{http_code}' \
    "${NOIP_UPDATE_URL}?hostname=${hostname}&myip=${ip}" 2>"${cfg}.err" || true)"
  err="$(cat "${cfg}.err" 2>/dev/null || true)"
  rm -f "$cfg" "${cfg}.err"
  if [ -n "$err" ]; then
    mirror_pi_warn "curl No-IP: ${err}"
  fi
  NOIP_HTTP_CODE="${raw##*$'\n'__HTTP__}"
  body="${raw%$'\n'__HTTP__*}"
  if [ "$body" = "$raw" ]; then
    NOIP_HTTP_CODE=""
    body="$raw"
  fi
  printf '%s' "$body"
}

noip_try_upnp() {
  local local_ip="$1"
  if [ "${NOIP_UPNP:-1}" != "1" ]; then
    printf '%s' skipped
    return 0
  fi
  if [ "$local_ip" = "${EVENT_LAN_IP:-192.168.100.1}" ]; then
    mirror_pi_log "UPnP saltato: IP locale ${local_ip} è la LAN evento"
    printf '%s' skipped
    return 0
  fi
  if ! command -v upnpc >/dev/null 2>&1; then
    mirror_pi_warn "miniupnpc assente: nessun port forward automatico (TCP 80, 443, 10022→22)"
    printf '%s' missing
    return 0
  fi
  local map lp ep failed=0 out rc
  # Word-split voluto: elenco "porta_locale:porta_esterna".
  # shellcheck disable=SC2086
  for map in $NOIP_UPNP_TCP_MAPS; do
    lp="${map%%:*}"
    ep="${map##*:}"
    if [[ ! "$lp" =~ ^[0-9]+$ ]] || [[ ! "$ep" =~ ^[0-9]+$ ]]; then
      mirror_pi_warn "mappa UPnP non valida: ${map}"
      failed=1
      continue
    fi
    rc=0
    out="$(upnpc -a "$local_ip" "$lp" "$ep" TCP 7200 2>&1)" || rc=$?
    if [ "$rc" -ne 0 ] || printf '%s\n' "$out" | grep -qiE 'No IGD|not found|failed|error'; then
      failed=1
      local flat
      flat="$(printf '%s' "$out" | tr '\n' ' ' || true)"
      mirror_pi_warn "UPnP TCP ${lp}→${ep} non riuscito (${flat:0:220})"
    else
      mirror_pi_log "UPnP TCP ${local_ip}:${lp} pubblicato sulla porta esterna ${ep}"
    fi
  done
  if [ "$failed" = "1" ]; then
    printf '%s' fail
  else
    printf '%s' ok
  fi
}

noip_warn_inbound() {
  local ip="$1" upnp_result="$2"
  if noip_ipv4_is_cgnat "$ip"; then
    mirror_pi_warn "IP ${ip} è Carrier-Grade NAT (100.64.0.0/10): non lo pubblico su ${NOIP_HOSTNAME}."
    return 0
  fi
  case "$upnp_result" in
    ok|skipped) return 0 ;;
  esac
  mirror_pi_warn "Il nome ${NOIP_HOSTNAME} può aggiornarsi, ma le porte in ingresso non risultano aperte via UPnP."
  mirror_pi_warn "Router nuovo: inoltra TCP 80, TCP 443 e TCP 10022→22 verso l'IP LAN del Pi."
  mirror_pi_warn "Hotspot telefono: quasi sempre CGNAT. Internet in uscita (sync verso www.kor35.it) funziona; dall'esterno il Pi non risponde su ${NOIP_HOSTNAME}."
}

noip_print_status() {
  local timer="n/d"
  if command -v systemctl >/dev/null 2>&1; then
    if systemctl is-active --quiet kor35-mirror-noip.timer 2>/dev/null; then
      timer="active"
    else
      timer="inactive"
    fi
  fi
  echo "hostname:    $(noip_state_value hostname)"
  echo "public_ip:   $(noip_state_value public_ip)"
  echo "result:      $(noip_state_value result)"
  echo "upnp:        $(noip_state_value upnp)"
  echo "halt:        $(noip_state_value halt_reason)"
  echo "timer:       ${timer}"
  echo "env:         ${NOIP_ENV_FILE}"
  if noip_credentials_ready; then
    echo "credenziali: presenti"
  else
    echo "credenziali: MANCANTI (${NOIP_ENV_FILE})"
  fi
}

noip_update_main() {
  local force=0 dry=0 status=0
  while [ $# -gt 0 ]; do
    case "$1" in
      --force) force=1; shift ;;
      --dry-run) dry=1; shift ;;
      --status) status=1; shift ;;
      -h|--help)
        sed -n '1,18p' "${BASH_SOURCE[0]}"
        return 0
        ;;
      *)
        mirror_pi_err "argomento non riconosciuto: $1"
        return 1
        ;;
    esac
  done

  NOIP_ENV_FILE="${NOIP_ENV_FILE:-/etc/kor35/noip.env}"
  NOIP_STATE_FILE="${NOIP_STATE_FILE:-/var/lib/kor35/noip.state}"
  NOIP_LOCK_FILE="${NOIP_LOCK_FILE:-/var/lib/kor35/noip.lock}"
  mkdir -p "$(dirname "$NOIP_STATE_FILE")" "$(dirname "$NOIP_LOCK_FILE")"

  mirror_pi_load_config
  # L'env di rete non deve coprire un NOIP_ENV_FILE passato dal chiamante.
  NOIP_ENV_FILE="${NOIP_ENV_FILE:-/etc/kor35/noip.env}"
  noip_load_env

  if [ "$status" = "1" ]; then
    noip_print_status
    return 0
  fi

  exec 9>"$NOIP_LOCK_FILE"
  if ! flock -w 60 9; then
    mirror_pi_warn "aggiornamento No-IP già in corso"
    return 0
  fi

  local src_ip="" public_ip="" now_epoch env_mtime
  now_epoch="$(date +%s)"
  env_mtime="$(noip_env_mtime)"

  src_ip="$(noip_default_src_ip || true)"
  if [ -z "$src_ip" ]; then
    mirror_pi_log "Nessuna route IPv4 verso Internet: No-IP non aggiornato (normale in evento offline)."
    return 0
  fi

  if ! public_ip="$(noip_detect_public_ipv4)"; then
    mirror_pi_warn "IP pubblico non rilevato: aggiornamento No-IP rimandato."
    return 1
  fi
  public_ip="$(printf '%s' "$public_ip" | tr -d '[:space:]')"

  STATE_HOSTNAME="$NOIP_HOSTNAME"
  STATE_PUBLIC_IP="$(noip_state_value public_ip)"
  STATE_RESULT="$(noip_state_value result)"
  STATE_UPDATED_EPOCH="$(noip_state_value updated_at_epoch)"
  STATE_HALT_REASON="$(noip_state_value halt_reason)"
  STATE_HALT_ENV_MTIME="$(noip_state_value halt_env_mtime)"
  STATE_UPNP="$(noip_state_value upnp)"

  if ! noip_ipv4_is_global "$public_ip"; then
    STATE_PUBLIC_IP="$public_ip"
    STATE_RESULT="nonglobal"
    STATE_UPDATED_EPOCH="$now_epoch"
    noip_write_state
    if noip_ipv4_is_cgnat "$public_ip"; then
      noip_warn_inbound "$public_ip" "fail"
    else
      mirror_pi_warn "IP rilevato ${public_ip} non è pubblico: non lo pubblico su ${NOIP_HOSTNAME}."
    fi
    return 0
  fi

  if [ "$dry" = "1" ]; then
    local decision
    decision="$(noip_should_update "$STATE_PUBLIC_IP" "${STATE_UPDATED_EPOCH:-0}" "$now_epoch" "$public_ip" "$force" "$NOIP_REFRESH_SEC")"
    echo "hostname:     ${NOIP_HOSTNAME}"
    echo "ip_pubblico:  ${public_ip}"
    echo "ip_locale:    ${src_ip}"
    echo "aggiornare:   ${decision}"
    echo "upnp:         ${NOIP_UPNP}"
    if noip_credentials_ready; then
      echo "credenziali:  presenti"
    else
      echo "credenziali:  MANCANTI"
    fi
    return 0
  fi

  if ! noip_credentials_ready; then
    mirror_pi_warn "Credenziali No-IP assenti in ${NOIP_ENV_FILE}."
    mirror_pi_warn "Compila username/password (account No-IP o DDNS key), poi: sudo systemctl start kor35-mirror-noip.service"
    mirror_pi_warn "Disattiva il DUC sul PC Windows, altrimenti i due client si sovrascrivono."
    return 0
  fi

  if ! noip_hostname_valid "$NOIP_HOSTNAME"; then
    mirror_pi_err "NOIP_HOSTNAME non valido: ${NOIP_HOSTNAME}"
    return 1
  fi

  if [ "$force" != "1" ] && [ -n "$STATE_HALT_REASON" ] && [ "$STATE_HALT_ENV_MTIME" = "$env_mtime" ]; then
    mirror_pi_warn "No-IP fermo (${STATE_HALT_REASON}). Aggiorna ${NOIP_ENV_FILE} oppure rilancia con --force."
    return 0
  fi

  local prev_ip prev_epoch prev_upnp upnp_result
  prev_ip="$(noip_state_value public_ip)"
  prev_epoch="$(noip_state_value updated_at_epoch)"
  prev_upnp="$(noip_state_value upnp)"
  upnp_result="$(noip_try_upnp "$src_ip")"
  STATE_UPNP="$upnp_result"

  local decision
  decision="$(noip_should_update "$prev_ip" "${prev_epoch:-0}" "$now_epoch" "$public_ip" "$force" "$NOIP_REFRESH_SEC")"
  # File credenziali aggiornato dopo un halt: ritenta anche se l'IP non è cambiato.
  if [ "$decision" = "no" ] && [ -n "$STATE_HALT_REASON" ] && [ "$STATE_HALT_ENV_MTIME" != "$env_mtime" ]; then
    decision="yes"
  fi

  if [ "$decision" = "no" ]; then
    STATE_HOSTNAME="$NOIP_HOSTNAME"
    STATE_PUBLIC_IP="$public_ip"
    STATE_RESULT="${STATE_RESULT:-nochg}"
    STATE_UPDATED_EPOCH="${prev_epoch:-0}"
    if [ "$upnp_result" != "ok" ] && [ "$upnp_result" != "skipped" ] && [ "$prev_upnp" != "$upnp_result" ]; then
      noip_warn_inbound "$public_ip" "$upnp_result"
    fi
    noip_write_state
    mirror_pi_log "No-IP invariato (${public_ip} su ${NOIP_HOSTNAME}), UPnP=${upnp_result}."
    return 0
  fi

  NOIP_HTTP_CODE=""
  local body code
  body="$(noip_http_update "$NOIP_HOSTNAME" "$public_ip")"
  code="$(noip_classify_response "$body")"
  if [ -z "$code" ] && [ "${NOIP_HTTP_CODE:-}" = "401" ]; then
    code="badauth"
  fi

  STATE_HOSTNAME="$NOIP_HOSTNAME"
  STATE_UPNP="$upnp_result"
  STATE_RESULT="$code"

  case "$code" in
    good|nochg)
      STATE_PUBLIC_IP="$public_ip"
      STATE_UPDATED_EPOCH="$now_epoch"
      STATE_HALT_REASON=""
      STATE_HALT_ENV_MTIME="0"
      noip_write_state
      mirror_pi_log "No-IP ${code} ${public_ip} → ${NOIP_HOSTNAME} (UPnP=${upnp_result})."
      if [ "$upnp_result" != "ok" ] && [ "$upnp_result" != "skipped" ]; then
        noip_warn_inbound "$public_ip" "$upnp_result"
      fi
      return 0
      ;;
  esac

  # Non marcare l'IP come pubblicato: al giro dopo si ritenta.
  STATE_PUBLIC_IP="$prev_ip"
  STATE_UPDATED_EPOCH="${prev_epoch:-0}"

  if noip_response_is_fatal "$code"; then
    STATE_HALT_REASON="$code"
    STATE_HALT_ENV_MTIME="$env_mtime"
    noip_write_state
    mirror_pi_err "No-IP ha rifiutato l'aggiornamento (${code}). Controllo ${NOIP_ENV_FILE}. Risposta: ${body}"
    mirror_pi_err "Nessun altro tentativo finché il file credenziali non cambia, oppure con --force."
    return 1
  fi

  STATE_UPDATED_EPOCH=0
  STATE_RESULT="${code:-error}"
  noip_write_state
  mirror_pi_warn "No-IP risposta inattesa (HTTP ${NOIP_HTTP_CODE:-?}): ${body:-vuota}. Riprovo al prossimo giro."
  return 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  noip_update_main "$@"
fi
