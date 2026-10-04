#!/usr/bin/env bash
# Test locali del client No-IP (nessuna rete, nessun segreto).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../mirror_noip_update.sh
source "$ROOT/scripts/mirror_noip_update.sh"

FAILURES=0
fail() {
  echo "FAIL: $*" >&2
  FAILURES=$((FAILURES + 1))
}

assert_eq() {
  local got="$1" want="$2" label="$3"
  if [ "$got" != "$want" ]; then
    fail "${label}: atteso '${want}', ottenuto '${got}'"
  fi
}

noip_ipv4_is_global "8.8.8.8" || fail "8.8.8.8 dovrebbe essere globale"
noip_ipv4_is_global "2.34.231.167" || fail "IP casa dovrebbe essere globale"
noip_ipv4_is_global "172.32.0.1" || fail "172.32 è fuori dal range privato"
if noip_ipv4_is_global "192.168.1.200"; then fail "LAN non è globale"; fi
if noip_ipv4_is_global "10.1.2.3"; then fail "10/8 non è globale"; fi
if noip_ipv4_is_global "172.16.5.5"; then fail "172.16/12 non è globale"; fi
if noip_ipv4_is_global "127.0.0.1"; then fail "loopback"; fi
if noip_ipv4_is_global "100.64.1.1"; then fail "CGNAT non è globale"; fi
if noip_ipv4_is_global "0.0.0.0"; then fail "0/8"; fi
if noip_ipv4_is_global "1.2.3.256"; then fail "ottetto 256"; fi
noip_ipv4_is_global "100.63.255.255" || fail "100.63 è fuori CGNAT"
noip_ipv4_is_global "100.128.0.1" || fail "100.128 è fuori CGNAT"
noip_ipv4_is_cgnat "100.127.255.255" || fail "bordo alto CGNAT"
if noip_ipv4_is_cgnat "8.8.8.8"; then fail "8.8.8.8 non è CGNAT"; fi

assert_eq "$(noip_classify_response "good 203.0.113.10")" "good" "classify good"
assert_eq "$(noip_classify_response $'nochg 203.0.113.10\r')" "nochg" "classify nochg"
assert_eq "$(noip_classify_response "badauth")" "badauth" "classify badauth"
assert_eq "$(noip_classify_response "")" "" "classify vuoto"
noip_response_is_fatal "badauth" || fail "badauth fatale"
noip_response_is_fatal "!donator" || fail "!donator fatale"
if noip_response_is_fatal "911"; then fail "911 non è fatale"; fi
if noip_response_is_fatal "good"; then fail "good non è fatale"; fi

assert_eq "$(noip_should_update "" 0 100 "203.0.113.10" 0 86400)" "yes" "primo update"
assert_eq "$(noip_should_update "203.0.113.10" 100 200 "203.0.113.10" 0 86400)" "no" "IP uguale e fresco"
assert_eq "$(noip_should_update "203.0.113.10" 100 90000 "203.0.113.10" 0 86400)" "yes" "refresh scaduto"
assert_eq "$(noip_should_update "198.51.100.8" 100 200 "203.0.113.10" 0 86400)" "yes" "IP cambiato"
assert_eq "$(noip_should_update "203.0.113.10" 100 200 "203.0.113.10" 1 86400)" "yes" "force"

HTTP_BODY="good 203.0.113.10"
HTTP_LOG=""

noip_http_update() {
  printf '%s %s\n' "$1" "$2" >>"$HTTP_LOG"
  NOIP_HTTP_CODE="200"
  printf '%s' "$HTTP_BODY"
}

http_calls() {
  if [ ! -f "${HTTP_LOG:-}" ]; then
    printf '%s' 0
    return 0
  fi
  wc -l <"$HTTP_LOG" | tr -d ' '
}

last_http_field() {
  local n="$1"
  [ -f "${HTTP_LOG:-}" ] || return 0
  tail -n 1 "$HTTP_LOG" | awk -v n="$n" '{print $n}'
}

noip_try_upnp() {
  printf '%s' skipped
}

setup_env() {
  TMP="$(mktemp -d)"
  NOIP_ENV_FILE="${TMP}/noip.env"
  NOIP_STATE_FILE="${TMP}/noip.state"
  NOIP_LOCK_FILE="${TMP}/noip.lock"
  NOIP_PUBLIC_IP_OVERRIDE="203.0.113.10"
  NOIP_SRC_IP_OVERRIDE="192.168.1.200"
  NOIP_ASSUME_OFFLINE=0
  HTTP_LOG="${TMP}/http.log"
  : >"$HTTP_LOG"
  HTTP_BODY="good 203.0.113.10"
  cat >"$NOIP_ENV_FILE" <<'EOF'
NOIP_USERNAME="user@kor35.it"
NOIP_PASSWORD="secret"
NOIP_HOSTNAME="kor35.ddns.net"
NOIP_UPNP="0"
NOIP_REFRESH_SEC="86400"
EOF
}

setup_env
noip_update_main --dry-run >/dev/null
assert_eq "$(http_calls)" "0" "dry-run non chiama No-IP"

setup_env
noip_update_main
assert_eq "$(http_calls)" "1" "primo aggiornamento"
assert_eq "$(last_http_field 1)" "kor35.ddns.net" "hostname"
assert_eq "$(last_http_field 2)" "203.0.113.10" "myip"
assert_eq "$(noip_state_value result)" "good" "stato good"
noip_update_main
assert_eq "$(http_calls)" "1" "secondo giro non ripete se l'IP è fresco"
noip_update_main --force
assert_eq "$(http_calls)" "2" "force ripete"

setup_env
NOIP_PUBLIC_IP_OVERRIDE="198.51.100.20"
HTTP_BODY="nochg 198.51.100.20"
noip_update_main
assert_eq "$(noip_state_value result)" "nochg" "nochg"
assert_eq "$(noip_state_value public_ip)" "198.51.100.20" "ip salvato"

setup_env
HTTP_BODY="badauth"
set +e
noip_update_main --force
rc=$?
set -e
assert_eq "$rc" "1" "badauth esce 1"
assert_eq "$(http_calls)" "1" "badauth una chiamata"
assert_eq "$(noip_state_value halt_reason)" "badauth" "halt"
noip_update_main
assert_eq "$(http_calls)" "1" "halt non ritenta"
set +e
noip_update_main --force
rc=$?
set -e
assert_eq "$rc" "1" "force su badauth esce ancora 1"
assert_eq "$(http_calls)" "2" "force sblocca l'halt"
noip_update_main
assert_eq "$(http_calls)" "2" "halt di nuovo attivo"

setup_env
printf 'NOIP_USERNAME=%q\nNOIP_PASSWORD=%q\nNOIP_HOSTNAME=%q\nNOIP_UPNP=%q\nNOIP_REFRESH_SEC=%q\n' \
  "CHANGE_ME" "CHANGE_ME" "kor35.ddns.net" "0" "86400" >"$NOIP_ENV_FILE"
noip_update_main
assert_eq "$(http_calls)" "0" "placeholder non chiama l'API"

setup_env
NOIP_ASSUME_OFFLINE=1
noip_update_main
assert_eq "$(http_calls)" "0" "offline non chiama l'API"

setup_env
NOIP_PUBLIC_IP_OVERRIDE="100.64.12.1"
noip_update_main
assert_eq "$(http_calls)" "0" "CGNAT non viene pubblicato"
assert_eq "$(noip_state_value result)" "nonglobal" "stato nonglobal"

setup_env
NOIP_PUBLIC_IP_OVERRIDE="203.0.113.10"
HTTP_BODY="good 203.0.113.10"
noip_update_main
# Password con virgolette e backslash: il file env è source-abile e non finisce nell'URL.
printf 'NOIP_USERNAME=%q\nNOIP_PASSWORD=%q\nNOIP_HOSTNAME=%q\nNOIP_UPNP=%q\nNOIP_REFRESH_SEC=%q\n' \
  'user@kor35.it' 'p"a\ss' 'kor35.ddns.net' '0' '86400' >"$NOIP_ENV_FILE"
# shellcheck disable=SC1090
source "$NOIP_ENV_FILE"
assert_eq "$NOIP_PASSWORD" 'p"a\ss' "password quotata"
escaped="$(noip_curl_escape "$NOIP_PASSWORD")"
assert_eq "$escaped" 'p\"a\\ss' "escape curl"

if [ "$FAILURES" -ne 0 ]; then
  echo "${FAILURES} test falliti" >&2
  exit 1
fi
echo "OK test_mirror_noip_update"
