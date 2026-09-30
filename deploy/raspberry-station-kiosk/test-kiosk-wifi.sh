#!/usr/bin/env bash
# Simula NetworkManager: kor35-larp deve vincere sulla rete di casa.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="${ROOT}/kor35-kiosk-wifi.sh"
PASS=0
FAIL=0

fail() {
  echo "FAIL: $*" >&2
  FAIL=$((FAIL + 1))
}

ok() {
  echo "OK: $*"
  PASS=$((PASS + 1))
}

new_case() {
  local dir="$1"
  rm -rf "$dir"
  mkdir -p "$dir/bin" "$dir/state"
  cp "$dir/../stub-nmcli.sh" "$dir/bin/nmcli" 2>/dev/null || true
  cat >"$dir/env" <<'EOF'
KIOSK_WIFI_PRIMARY_SSID=kor35-larp
KIOSK_WIFI_PRIMARY_PSK=secret-larp
KIOSK_WIFI_FALLBACK_SSID=Casa
KIOSK_WIFI_FALLBACK_PSK=secret-casa
KIOSK_WIFI_IFACE=wlan0
KIOSK_WIFI_SCAN_WAIT=0
KIOSK_WIFI_PRIMARY_ATTEMPTS=6
EOF
  printf '%s\n' "Casa" >"$dir/state/current"
  printf '%s\n' "0" >"$dir/state/rescans"
  printf '%s\n' "1" >"$dir/state/reveal_after"
  : >"$dir/state/ups"
  : >"$dir/state/iwscan"
  printf '%s\n' "Casa|Casa|802-11-wireless|0" >"$dir/state/profiles"
}

write_stubs() {
  local dir="$1"
  mkdir -p "$dir/bin" "$dir/state"
  cat >"$dir/bin/nmcli" <<'EOS'
#!/usr/bin/env bash
STATE="${KIOSK_WIFI_STUB_STATE:?}"
printf '%s\n' "$*" >>"$STATE/calls"
reveal() {
  local n
  n="$(cat "$STATE/rescans")"
  [ "$n" -ge "$(cat "$STATE/reveal_after")" ]
}
list_ssids() {
  echo "Casa"
  if reveal; then
    echo "kor35-larp"
  fi
}
profile_field() {
  local name="$1" idx="$2" line
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    IFS='|' read -r pname pssid ptype prio <<<"$line"
    if [ "$pname" = "$name" ]; then
      case "$idx" in
        2) printf '%s\n' "$pssid" ;;
        3) printf '%s\n' "$ptype" ;;
      esac
      return 0
    fi
  done <"$STATE/profiles"
  return 1
}
if [ "${1:-}" = "-t" ]; then
  case "${2:-}" in
    -f)
      case "${3:-}" in
        DEVICE,TYPE) printf '%s\n' "wlan0:wifi" ;;
        ACTIVE,SSID)
          printf 'yes:%s\n' "$(cat "$STATE/current")"
          ;;
        SSID) list_ssids ;;
      esac
      ;;
  esac
  exit 0
fi
if [ "${1:-}" = "-g" ]; then
  field="${2:-}"
  if [ "$field" = "NAME" ]; then
    awk -F'|' 'NF { print $1 }' "$STATE/profiles"
    exit 0
  fi
  name="${5:-}"
  case "$field" in
    802-11-wireless.ssid) profile_field "$name" 2 ;;
    connection.type) profile_field "$name" 3 ;;
  esac
  exit 0
fi
if [ "${1:-}" = "device" ] && [ "${2:-}" = "wifi" ] && [ "${3:-}" = "rescan" ]; then
  n="$(cat "$STATE/rescans")"
  printf '%s\n' "$((n + 1))" >"$STATE/rescans"
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "add" ]; then
  name=""
  ssid=""
  prev=""
  for arg in "$@"; do
    if [ "$prev" = "con-name" ]; then name="$arg"; fi
    if [ "$prev" = "ssid" ]; then ssid="$arg"; fi
    prev="$arg"
  done
  printf '%s|%s|802-11-wireless|100\n' "$name" "$ssid" >>"$STATE/profiles"
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "modify" ]; then
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "up" ]; then
  name="${3:-}"
  ssid="$(profile_field "$name" 2 || true)"
  printf '%s\n' "$name" >>"$STATE/ups"
  [ -n "$ssid" ] && printf '%s\n' "$ssid" >"$STATE/current"
  exit 0
fi
echo "nmcli stub: comando non gestito: $*" >&2
exit 1
EOS
  cat >"$dir/bin/iw" <<'EOS'
#!/usr/bin/env bash
STATE="${KIOSK_WIFI_STUB_STATE:?}"
if [ "${1:-}" = "dev" ] && [ "${3:-}" = "link" ]; then
  ssid="$(cat "$STATE/current")"
  if [ -n "$ssid" ]; then
    printf '\tSSID: %s\n' "$ssid"
  else
    printf '%s\n' "Not connected."
  fi
  exit 0
fi
if [ "${1:-}" = "dev" ] && [ "${3:-}" = "scan" ]; then
  if [ -s "$STATE/iwscan" ]; then
    while IFS= read -r ssid; do
      [ -n "$ssid" ] || continue
      printf '\tSSID: %s\n' "$ssid"
    done <"$STATE/iwscan"
  fi
  exit 0
fi
exit 0
EOS
  chmod 755 "$dir/bin/nmcli" "$dir/bin/iw"
}

run_helper() {
  local dir="$1"
  shift
  PATH="$dir/bin:$PATH" \
    KIOSK_WIFI_STUB_STATE="$dir/state" \
    KOR35_KIOSK_STATION_ENV="$dir/env" \
    "$HELPER" "$@"
}

assert_last_up() {
  local dir="$1" expected="$2" got
  got="$(tail -n 1 "$dir/state/ups")"
  if [ "$got" = "$expected" ]; then
    ok "attivato ${expected}"
  else
    fail "atteso up ${expected}, ottenuto '${got}'"
  fi
}

assert_not_up() {
  local dir="$1" name="$2"
  if grep -qx "$name" "$dir/state/ups"; then
    fail "${name} non doveva essere attivato"
  else
    ok "${name} non attivato"
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Entrambe visibili: non restare su Casa.
D="$TMP/both"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
if run_helper "$D" ensure >/tmp/kiosk-wifi-both.log 2>&1; then
  ok "ensure con entrambe le reti"
else
  fail "ensure doveva riuscire (entrambe visibili)"; cat /tmp/kiosk-wifi-both.log >&2 || true
fi
assert_last_up "$D" "kor35-larp"
assert_not_up "$D" "Casa"
if grep -q "Casa" "$D/state/current"; then
  fail "ancora sulla rete di casa"
else
  ok "ssid corrente kor35-larp"
fi

# 2. kor35-larp compare solo al terzo scan: si aspetta, non si accontenta di Casa.
D="$TMP/late"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "3" >"$D/state/reveal_after"
if run_helper "$D" ensure >/tmp/kiosk-wifi-late.log 2>&1; then
  ok "ensure aspetta la rete evento"
else
  fail "ensure doveva aspettare kor35-larp"; cat /tmp/kiosk-wifi-late.log >&2 || true
fi
assert_last_up "$D" "kor35-larp"
assert_not_up "$D" "Casa"

# 3. Già in casa, Omada visibile: prefer cambia rete.
D="$TMP/prefer"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "Evento|kor35-larp|802-11-wireless|0" >>"$D/state/profiles"
printf '%s\n' "" >"$D/env.psk"
# PSK vuota: deve usare il profilo salvato "Evento", non il nome dell'SSID.
cat >"$D/env" <<'EOF'
KIOSK_WIFI_PRIMARY_SSID=kor35-larp
KIOSK_WIFI_PRIMARY_PSK=
KIOSK_WIFI_FALLBACK_SSID=Casa
KIOSK_WIFI_FALLBACK_PSK=secret-casa
KIOSK_WIFI_IFACE=wlan0
KIOSK_WIFI_SCAN_WAIT=0
KIOSK_WIFI_PRIMARY_ATTEMPTS=4
EOF
if run_helper "$D" prefer >/tmp/kiosk-wifi-prefer.log 2>&1; then
  ok "prefer passa a kor35-larp"
else
  fail "prefer doveva passare a kor35-larp"; cat /tmp/kiosk-wifi-prefer.log >&2 || true
fi
assert_last_up "$D" "Evento"

# 4. Omada assente: prefer non riaggancia la rete di casa.
D="$TMP/absent"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "99" >"$D/state/reveal_after"
set +e
run_helper "$D" prefer >/tmp/kiosk-wifi-absent.log 2>&1
rc=$?
set -e
if [ "$rc" -eq 10 ]; then
  ok "prefer esce 10 se kor35-larp non c'è"
else
  fail "prefer doveva uscire 10, codice ${rc}"
fi
if [ -s "$D/state/ups" ]; then
  fail "prefer non doveva attivare profili: $(cat "$D/state/ups")"
else
  ok "nessuna attivazione senza kor35-larp"
fi

# 5. nmcli non elenca la rete, iw sì (scan del Pi mentre è associato a casa).
D="$TMP/iw"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "99" >"$D/state/reveal_after"
printf '%s\n' "kor35-larp" >"$D/state/iwscan"
if run_helper "$D" prefer >/tmp/kiosk-wifi-iw.log 2>&1; then
  ok "prefer usa lo scan iw"
else
  fail "prefer doveva vedere kor35-larp via iw"; cat /tmp/kiosk-wifi-iw.log >&2 || true
fi
assert_last_up "$D" "kor35-larp"

echo "--- ${PASS} ok, ${FAIL} fail ---"
[ "$FAIL" -eq 0 ]
