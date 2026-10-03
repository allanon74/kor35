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
if [ "${1:-}" = "-w" ]; then
  shift 2
fi
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
    IFS='|' read -r pname pssid ptype prio pts <<<"$line"
    if [ "$pname" = "$name" ]; then
      case "$idx" in
        2) printf '%s\n' "$pssid" ;;
        3) printf '%s\n' "$ptype" ;;
        5) printf '%s\n' "${pts:-0}" ;;
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
        DEVICE,TYPE)
          if [ -s "$STATE/devices" ]; then
            cat "$STATE/devices"
          else
            printf '%s\n' "wlan0:wifi"
          fi
          ;;
        ACTIVE,SSID)
          printf 'yes:%s\n' "$(cat "$STATE/current")"
          ;;
        SSID) list_ssids ;;
        NAME,TYPE)
          cur="$(cat "$STATE/current")"
          while IFS= read -r line; do
            [ -n "$line" ] || continue
            IFS='|' read -r pname pssid ptype prio pts <<<"$line"
            if [ -n "$cur" ] && [ "$pssid" = "$cur" ]; then
              printf '%s:%s\n' "$pname" "${ptype:-802-11-wireless}"
            fi
          done <"$STATE/profiles"
          ;;
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
    connection.timestamp) profile_field "$name" 5 ;;
  esac
  exit 0
fi
if [ "${1:-}" = "device" ] && [ "${2:-}" = "wifi" ] && [ "${3:-}" = "rescan" ]; then
  n="$(cat "$STATE/rescans")"
  printf '%s\n' "$((n + 1))" >"$STATE/rescans"
  exit 0
fi
if [ "${1:-}" = "device" ] && [ "${2:-}" = "wifi" ] && [ "${3:-}" = "connect" ]; then
  ssid="${4:-}"
  printf '%s|%s|802-11-wireless|100|%s\n' "$ssid" "$ssid" "200" >>"$STATE/profiles"
  printf '%s\n' "$ssid" >>"$STATE/ups"
  printf '%s\n' "$ssid" >"$STATE/current"
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
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "down" ]; then
  name="${3:-}"
  ssid="$(profile_field "$name" 2 || true)"
  printf '%s\n' "$name" >>"$STATE/downs"
  if [ -n "$ssid" ] && [ "$(cat "$STATE/current")" = "$ssid" ]; then
    printf '%s\n' "" >"$STATE/current"
  fi
  exit 0
fi
if [ "${1:-}" = "device" ] && [ "${2:-}" = "disconnect" ]; then
  printf '%s\n' "" >"$STATE/current"
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "up" ]; then
  name="${3:-}"
  ssid="$(profile_field "$name" 2 || true)"
  if [ -f "$STATE/require_down" ] && [ -n "$(cat "$STATE/current")" ] && [ "$(cat "$STATE/current")" != "$ssid" ]; then
    echo "Error: device busy with $(cat "$STATE/current")" >&2
    exit 1
  fi
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

assert_no_psk_rewrite() {
  local dir="$1"
  if grep -q 'wifi-sec.psk' "$dir/state/calls"; then
    fail "ha riscritto la password del profilo"
  else
    ok "password del profilo non toccata"
  fi
}

# 6. Il profilo usato a mano vince su quello rotto, senza riscrivere la PSK.
D="$TMP/manual"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "Casa|Casa|802-11-wireless|0|20" >"$D/state/profiles"
printf '%s\n' "rotto|kor35-larp|802-11-wireless|0|1" >>"$D/state/profiles"
printf '%s\n' "Desktop|kor35-larp|802-11-wireless|0|99" >>"$D/state/profiles"
if run_helper "$D" ensure >/tmp/kiosk-wifi-manual.log 2>&1; then
  ok "ensure usa il profilo del desktop"
else
  fail "ensure doveva usare il profilo manuale"; cat /tmp/kiosk-wifi-manual.log >&2 || true
fi
assert_last_up "$D" "Desktop"
assert_not_up "$D" "rotto"
assert_no_psk_rewrite "$D"

# 7. Non attivare p2p-dev-wlan0: lì la connessione fallisce e si torna in casa.
D="$TMP/p2p"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "p2p-dev-wlan0:wifi" >"$D/state/devices"
printf '%s\n' "wlan0:wifi" >>"$D/state/devices"
printf '%s\n' "Desktop|kor35-larp|802-11-wireless|0|99" >>"$D/state/profiles"
if run_helper "$D" prefer >/tmp/kiosk-wifi-p2p.log 2>&1; then
  ok "prefer ignora p2p"
else
  fail "prefer doveva usare wlan0"; cat /tmp/kiosk-wifi-p2p.log >&2 || true
fi
if grep -q 'ifname p2p-dev-wlan0' "$D/state/calls"; then
  fail "ha usato p2p-dev-wlan0"
else
  ok "interfaccia p2p non usata"
fi
if grep -q -- '-w 15 connection up Desktop ifname wlan0' "$D/state/calls"; then
  ok "attivato Desktop su wlan0"
else
  fail "manca connection up Desktop su wlan0"
fi

# 8. Già su Casa, Omada non in scan (tipico da associati): usa il profilo e stacca Casa.
D="$TMP/busy-home"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
: >"$D/state/require_down"
printf '%s\n' "99" >"$D/state/reveal_after"
printf '%s\n' "Desktop|kor35-larp|802-11-wireless|0|99" >>"$D/state/profiles"
if run_helper "$D" prefer >/tmp/kiosk-wifi-busy.log 2>&1; then
  ok "prefer stacca Casa anche se kor35-larp non è in scan"
else
  fail "prefer doveva staccare Casa e usare il profilo evento"; cat /tmp/kiosk-wifi-busy.log >&2 || true
fi
assert_last_up "$D" "Desktop"
if grep -qx "Casa" "$D/state/downs"; then
  ok "ha staccato Casa"
else
  fail "doveva fare connection down Casa"
fi
if grep -q "kor35-larp" "$D/state/current"; then
  ok "ora su kor35-larp"
else
  fail "corrente $(cat "$D/state/current")"
fi

# 9. SSID salvato kor35_larp (underscore): è la stessa rete evento.
D="$TMP/underscore"
write_stubs "$D"
new_case "$D"
write_stubs "$D"
printf '%s\n' "99" >"$D/state/reveal_after"
printf '%s\n' "Omada|kor35_larp|802-11-wireless|0|50" >>"$D/state/profiles"
if run_helper "$D" prefer >/tmp/kiosk-wifi-underscore.log 2>&1; then
  ok "prefer accetta kor35_larp come kor35-larp"
else
  fail "prefer doveva usare il profilo kor35_larp"; cat /tmp/kiosk-wifi-underscore.log >&2 || true
fi
assert_last_up "$D" "Omada"

echo "--- ${PASS} ok, ${FAIL} fail ---"
[ "$FAIL" -eq 0 ]
