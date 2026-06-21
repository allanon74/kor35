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
