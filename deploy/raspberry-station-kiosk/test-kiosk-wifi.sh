#!/usr/bin/env bash
# Il helper non stacca la rete attuale. Se l'evento è già su, non fa connection up.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="${ROOT}/kor35-kiosk-wifi.sh"
PASS=0
FAIL=0

fail() { echo "FAIL: $*" >&2; FAIL=$((FAIL + 1)); }
ok() { echo "OK: $*"; PASS=$((PASS + 1)); }

new_case() {
  local dir="$1"
  rm -rf "$dir"
  mkdir -p "$dir/bin" "$dir/state"
  printf '%s\n' "Casa" >"$dir/state/current"
  printf '%s\n' "Casa|Casa|10" >"$dir/state/profiles"
  printf '%s\n' "Evento|kor35-larp|50" >>"$dir/state/profiles"
  : >"$dir/state/ups"
  : >"$dir/state/downs"
  cat >"$dir/env" <<'EOF'
KIOSK_WIFI_PRIMARY_SSID=kor35-larp
KIOSK_WIFI_PRIMARY_PSK=
KIOSK_WIFI_IFACE=wlan0
EOF
  cat >"$dir/bin/nmcli" <<'EOS'
#!/usr/bin/env bash
STATE="${KIOSK_WIFI_STUB_STATE:?}"
printf '%s\n' "$*" >>"$STATE/calls"
profile_ssid() {
  local name="$1" line pname pssid
  while IFS= read -r line; do
    IFS='|' read -r pname pssid _ <<<"$line"
    if [ "$pname" = "$name" ]; then
      printf '%s\n' "$pssid"
      return 0
    fi
  done <"$STATE/profiles"
  return 1
}
if [ "${1:-}" = "-t" ] && [ "${2:-}" = "-f" ] && [ "${3:-}" = "DEVICE,TYPE" ]; then
  printf '%s\n' "wlan0:wifi"
  exit 0
fi
if [ "${1:-}" = "-t" ] && [ "${2:-}" = "-f" ] && [ "${3:-}" = "ACTIVE,SSID" ]; then
  printf 'yes:%s\n' "$(cat "$STATE/current")"
  exit 0
fi
if [ "${1:-}" = "-t" ] && [ "${2:-}" = "-f" ] && [ "${3:-}" = "NAME,TYPE" ]; then
  cur="$(cat "$STATE/current")"
  while IFS= read -r line; do
    IFS='|' read -r pname pssid _ <<<"$line"
    [ "$pssid" = "$cur" ] && printf '%s:802-11-wireless\n' "$pname"
  done <"$STATE/profiles"
  exit 0
fi
if [ "${1:-}" = "-g" ] && [ "${2:-}" = "NAME" ]; then
  awk -F'|' 'NF { print $1 }' "$STATE/profiles"
  exit 0
fi
if [ "${1:-}" = "-g" ] && [ "${2:-}" = "802-11-wireless.ssid" ]; then
  profile_ssid "${5:-}"
  exit 0
fi
if [ "${1:-}" = "-g" ] && [ "${2:-}" = "connection.timestamp" ]; then
  name="${5:-}"
  awk -F'|' -v n="$name" '$1==n { print $3 }' "$STATE/profiles"
  exit 0
fi
if [ "${1:-}" = "-w" ]; then
  shift 2
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "up" ]; then
  name="${3:-}"
  printf '%s\n' "$name" >>"$STATE/ups"
  ssid="$(profile_ssid "$name" || true)"
  [ -n "$ssid" ] && printf '%s\n' "$ssid" >"$STATE/current"
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "down" ]; then
  printf '%s\n' "${3:-}" >>"$STATE/downs"
  exit 0
fi
if [ "${1:-}" = "connection" ] && [ "${2:-}" = "modify" ]; then
  exit 0
fi
if [ "${1:-}" = "device" ]; then
  exit 0
fi
echo "nmcli stub: $*" >&2
exit 1
EOS
  cat >"$dir/bin/iw" <<'EOS'
#!/usr/bin/env bash
STATE="${KIOSK_WIFI_STUB_STATE:?}"
if [ "${1:-}" = "dev" ] && [ "${3:-}" = "link" ]; then
  ssid="$(cat "$STATE/current")"
  if [ -n "$ssid" ]; then
    printf '\tSSID: %s\n' "$ssid"
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

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

D="$TMP/already"
new_case "$D"
printf '%s\n' "kor35-larp" >"$D/state/current"
run_helper "$D" once >/tmp/kiosk-once-already.log
if [ -s "$D/state/ups" ]; then
  fail "già su kor35-larp non deve fare connection up"
else
  ok "già su kor35-larp: nessuna attivazione"
fi
if [ -s "$D/state/downs" ]; then
  fail "non deve staccare la rete"
else
  ok "nessuno stacco"
fi

D="$TMP/switch"
new_case "$D"
run_helper "$D" once >/tmp/kiosk-once-switch.log
if grep -qx "Evento" "$D/state/ups"; then
  ok "alza il profilo Evento"
else
  fail "doveva attivare Evento, ups=$(cat "$D/state/ups" 2>/dev/null || true)"
fi
if [ -s "$D/state/downs" ]; then
  fail "non deve fare connection down"
else
  ok "passa all'evento senza staccare a mano"
fi

D="$TMP/underscore"
new_case "$D"
printf '%s\n' "Omada|kor35_larp|80" >"$D/state/profiles"
printf '%s\n' "Casa" >"$D/state/current"
run_helper "$D" once >/tmp/kiosk-once-us.log
if grep -qx "Omada" "$D/state/ups"; then
  ok "kor35_larp conta come rete evento"
else
  fail "doveva attivare Omada"
fi

echo "--- ${PASS} ok, ${FAIL} fail ---"
[ "$FAIL" -eq 0 ]
