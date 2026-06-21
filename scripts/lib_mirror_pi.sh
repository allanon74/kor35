#!/usr/bin/env bash
# Libreria comune per script rete/diagnostica mirror Pi.
# shellcheck shell=bash

KOR35_MIRROR_CONFIG_DEFAULT="/etc/kor35/mirror-network.env"
KOR35_MIRROR_STATE_FILE_DEFAULT="/var/lib/kor35/mirror-network-mode"

mirror_pi_repo_root() {
  local lib_dir
  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$lib_dir/.." && pwd
}

mirror_pi_load_config() {
  local config_file="${KOR35_MIRROR_CONFIG:-$KOR35_MIRROR_CONFIG_DEFAULT}"
  KOR35_REPO_PATH="${KOR35_REPO_PATH:-/home/pi/kor35-replica}"
  EVENT_LAN_INTERFACE="${EVENT_LAN_INTERFACE:-eth0}"
  EVENT_LAN_IP="${EVENT_LAN_IP:-192.168.100.1}"
  EVENT_LAN_CIDR="${EVENT_LAN_CIDR:-24}"
  EVENT_DHCP_RANGE_START="${EVENT_DHCP_RANGE_START:-192.168.100.50}"
  EVENT_DHCP_RANGE_END="${EVENT_DHCP_RANGE_END:-192.168.100.200}"
  EMERGENCY_WIFI_INTERFACE="${EMERGENCY_WIFI_INTERFACE:-wlan0}"
  EMERGENCY_WIFI_SSID="${EMERGENCY_WIFI_SSID:-Pi_emergenza}"
  EMERGENCY_WIFI_IP="${EMERGENCY_WIFI_IP:-10.42.0.1}"
  EMERGENCY_WIFI_CIDR="${EMERGENCY_WIFI_CIDR:-24}"
  LOCAL_DNS_DOMAINS="${LOCAL_DNS_DOMAINS:-www.kor35.it,kor35.it,kor35.ddns.net}"
  INTERNET_CHECK_URL="${INTERNET_CHECK_URL:-https://www.kor35.it/api/healthz/}"
  INTERNET_CHECK_TIMEOUT_SEC="${INTERNET_CHECK_TIMEOUT_SEC:-8}"
  COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-kor35-replica}"

  if [ -f "$config_file" ]; then
    # shellcheck disable=SC1090
    source "$config_file"
  fi

  KOR35_BACKEND_ENV_FILE="${KOR35_BACKEND_ENV_FILE:-${KOR35_REPO_PATH}/backend/.env.mirror}"
  KOR35_MIRROR_STATE_FILE="${KOR35_MIRROR_STATE_FILE:-$KOR35_MIRROR_STATE_FILE_DEFAULT}"
}

mirror_pi_log() {
  echo "[mirror-pi] $*"
}

mirror_pi_warn() {
  echo "[mirror-pi] ATTENZIONE: $*" >&2
}

mirror_pi_err() {
  echo "[mirror-pi] ERRORE: $*" >&2
}

mirror_pi_detect_lan_interface() {
  local iface="${EVENT_LAN_INTERFACE:-eth0}"
  if ip link show "$iface" >/dev/null 2>&1; then
    echo "$iface"
    return 0
  fi
  for iface in en* end* eth*; do
    if [ -d "/sys/class/net/$iface" ] && [ "$iface" != "lo" ]; then
      echo "$iface"
      return 0
    fi
  done
  echo "${EVENT_LAN_INTERFACE:-eth0}"
  return 1
}

mirror_pi_has_internet() {
  local url="${1:-$INTERNET_CHECK_URL}"
  local timeout="${2:-$INTERNET_CHECK_TIMEOUT_SEC}"
  curl -fsS --max-time "$timeout" "$url" >/dev/null 2>&1
}

mirror_pi_compose_dir() {
  echo "${KOR35_REPO_PATH}/config/docker"
}

mirror_pi_write_mode_state() {
  local mode="$1"
  local state_file="${KOR35_MIRROR_STATE_FILE:-$KOR35_MIRROR_STATE_FILE_DEFAULT}"
  mkdir -p "$(dirname "$state_file")"
  printf '%s\n' "$mode" >"$state_file"
}

mirror_pi_read_mode_state() {
  local state_file="${KOR35_MIRROR_STATE_FILE:-$KOR35_MIRROR_STATE_FILE_DEFAULT}"
  if [ -f "$state_file" ]; then
    tr -d '[:space:]' <"$state_file"
  else
    echo "unknown"
  fi
}

mirror_pi_service_active() {
  if ! command -v systemctl >/dev/null 2>&1; then
    return 1
  fi
  systemctl is-active --quiet "$1" 2>/dev/null
}

mirror_pi_render_template() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|@EVENT_LAN_INTERFACE@|${EVENT_LAN_INTERFACE}|g" \
    -e "s|@EVENT_LAN_IP@|${EVENT_LAN_IP}|g" \
    -e "s|@EVENT_LAN_CIDR@|${EVENT_LAN_CIDR}|g" \
    -e "s|@EVENT_DHCP_RANGE_START@|${EVENT_DHCP_RANGE_START}|g" \
    -e "s|@EVENT_DHCP_RANGE_END@|${EVENT_DHCP_RANGE_END}|g" \
    -e "s|@EMERGENCY_WIFI_INTERFACE@|${EMERGENCY_WIFI_INTERFACE}|g" \
    -e "s|@EMERGENCY_WIFI_SSID@|${EMERGENCY_WIFI_SSID}|g" \
    -e "s|@EMERGENCY_WIFI_IP@|${EMERGENCY_WIFI_IP}|g" \
    -e "s|@EMERGENCY_WIFI_PASSPHRASE@|${EMERGENCY_WIFI_PASSPHRASE:-CHANGE_ME_EMERGENCY_PSK}|g" \
    -e "s|@LOCAL_DNS_DOMAINS@|${LOCAL_DNS_DOMAINS}|g" \
    "$src" >"$dst"
}

# Hotspot staff su wlan0 (10.42.0.1): NM Hotspot-Emergenza oppure hostapd systemd.
mirror_pi_try_nm_hotspot() {
  if ! command -v nmcli >/dev/null 2>&1; then
    return 1
  fi
  if ! nmcli -t -f NAME con show 2>/dev/null | grep -qx 'Hotspot-Emergenza'; then
    return 1
  fi

  if command -v rfkill >/dev/null 2>&1 && rfkill list wifi 2>/dev/null | grep -q 'Soft blocked: yes'; then
    rfkill unblock wifi 2>/dev/null || true
  fi
  nmcli radio wifi on 2>/dev/null || true
  nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed yes 2>/dev/null || true

  local active_on_wifi
  active_on_wifi="$(
    nmcli -t -f NAME,DEVICE con show --active 2>/dev/null \
      | awk -F: -v dev="$EMERGENCY_WIFI_INTERFACE" '$2 == dev {print $1}' \
      | grep -vx 'Hotspot-Emergenza' || true
  )"
  for con in $active_on_wifi; do
    nmcli con down "$con" 2>/dev/null || true
  done

  nmcli con modify Hotspot-Emergenza \
    connection.interface-name "$EMERGENCY_WIFI_INTERFACE" \
    connection.autoconnect yes 2>/dev/null || true

  if ! nmcli -t -f NAME con show --active 2>/dev/null | grep -qx 'Hotspot-Emergenza'; then
    local nm_err=""
    nm_err="$(nmcli con up Hotspot-Emergenza 2>&1)" || mirror_pi_warn "nmcli con up Hotspot-Emergenza: ${nm_err}"
  fi

  if mirror_pi_emergency_wifi_up; then
    return 0
  fi
  return 1
}

mirror_pi_recreate_nm_hotspot() {
  local psk="${EMERGENCY_WIFI_PASSPHRASE:-}"
  if [ -z "$psk" ] || [ "$psk" = "CHANGE_ME_EMERGENCY_PSK" ]; then
    return 1
  fi
  if ! command -v nmcli >/dev/null 2>&1; then
    return 1
  fi

  mirror_pi_log "Ricreo profilo NM Hotspot-Emergenza (${EMERGENCY_WIFI_SSID})"
  nmcli con down Hotspot-Emergenza 2>/dev/null || true
  nmcli con delete Hotspot-Emergenza 2>/dev/null || true
  nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed yes 2>/dev/null || true

  local nm_err=""
  nm_err="$(
    nmcli device wifi hotspot \
      ifname "$EMERGENCY_WIFI_INTERFACE" \
      con-name Hotspot-Emergenza \
      ssid "$EMERGENCY_WIFI_SSID" \
      password "$psk" \
      ipv4.method shared \
      connection.autoconnect yes 2>&1
  )" || {
    mirror_pi_warn "nmcli device wifi hotspot fallito: ${nm_err}"
    return 1
  }

  mirror_pi_emergency_wifi_up
}

mirror_pi_try_hostapd_hotspot() {
  if [ ! -f /etc/kor35/hostapd-emergency.conf ]; then
    mirror_pi_warn "manca /etc/kor35/hostapd-emergency.conf — esegui install_mirror_network.sh"
    return 1
  fi
  if [ -z "${EMERGENCY_WIFI_PASSPHRASE:-}" ] || [ "${EMERGENCY_WIFI_PASSPHRASE}" = "CHANGE_ME_EMERGENCY_PSK" ]; then
    mirror_pi_warn "EMERGENCY_WIFI_PASSPHRASE non configurata in /etc/kor35/mirror-network.env"
    return 1
  fi

  if command -v nmcli >/dev/null 2>&1; then
    nmcli con down Hotspot-Emergenza 2>/dev/null || true
    nmcli dev disconnect "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null || true
    nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed no 2>/dev/null || true
  fi

  systemctl enable kor35-mirror-emergency-wifi.service 2>/dev/null || true
  if mirror_pi_service_active kor35-mirror-emergency-wifi.service; then
    systemctl restart kor35-mirror-emergency-wifi.service || return 1
  else
    systemctl start kor35-mirror-emergency-wifi.service || return 1
  fi

  sleep 1
  mirror_pi_emergency_wifi_up
}

mirror_pi_ensure_emergency_wifi() {
  if mirror_pi_try_nm_hotspot; then
    mirror_pi_log "WiFi emergenza: NetworkManager Hotspot-Emergenza"
    return 0
  fi

  if mirror_pi_recreate_nm_hotspot; then
    mirror_pi_log "WiFi emergenza: NetworkManager Hotspot-Emergenza (ricreato)"
    return 0
  fi

  if mirror_pi_try_hostapd_hotspot; then
    mirror_pi_log "WiFi emergenza: hostapd (kor35-mirror-emergency-wifi.service)"
    return 0
  fi

  if command -v nmcli >/dev/null 2>&1; then
    nmcli dev set "$EMERGENCY_WIFI_INTERFACE" managed no 2>/dev/null || true
  fi
  if ! ip -4 addr show dev "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null | grep -q "${EMERGENCY_WIFI_IP}/"; then
    ip link set "$EMERGENCY_WIFI_INTERFACE" up 2>/dev/null || true
    ip addr add "${EMERGENCY_WIFI_IP}/${EMERGENCY_WIFI_CIDR}" dev "$EMERGENCY_WIFI_INTERFACE" 2>/dev/null || true
  fi
  return 1
}

mirror_pi_diagnose_emergency_wifi() {
  echo ""
  mirror_pi_log "=== Diagnostica WiFi emergenza ==="
  echo "Interfaccia attesa: ${EMERGENCY_WIFI_INTERFACE:-wlan0} SSID=${EMERGENCY_WIFI_SSID:-?} IP=${EMERGENCY_WIFI_IP:-10.42.0.1}"
  if command -v rfkill >/dev/null 2>&1; then
    echo "--- rfkill ---"
    rfkill list 2>/dev/null || true
  fi
  if command -v nmcli >/dev/null 2>&1; then
    echo "--- nmcli device ---"
    nmcli -f DEVICE,TYPE,STATE,CONNECTION device 2>/dev/null || true
    echo "--- nmcli Hotspot-Emergenza ---"
    nmcli con show Hotspot-Emergenza 2>/dev/null | head -40 || echo "(profilo assente)"
  fi
  echo "--- ip wlan ---"
  ip -4 addr show dev "${EMERGENCY_WIFI_INTERFACE:-wlan0}" 2>/dev/null || true
  echo "--- hostapd unit ---"
  systemctl is-enabled kor35-mirror-emergency-wifi.service 2>/dev/null || true
  systemctl is-active kor35-mirror-emergency-wifi.service 2>/dev/null || true
  journalctl -u kor35-mirror-emergency-wifi.service -n 15 --no-pager 2>/dev/null || true
}

mirror_pi_emergency_wifi_up() {
  if mirror_pi_service_active kor35-mirror-emergency-wifi.service; then
    return 0
  fi
  if command -v nmcli >/dev/null 2>&1; then
    if nmcli -t -f NAME con show --active 2>/dev/null | grep -qx 'Hotspot-Emergenza'; then
      return 0
    fi
  fi
  if ip -4 addr show dev "${EMERGENCY_WIFI_INTERFACE:-wlan0}" 2>/dev/null | grep -q "${EMERGENCY_WIFI_IP:-10.42.0.1}/"; then
    return 0
  fi
  return 1
}
