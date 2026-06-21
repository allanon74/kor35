#!/usr/bin/env bash
set -euo pipefail

# Installa configurazione rete mirror Pi (dnsmasq evento, hostapd emergenza, systemd).
#
# Uso sul Pi:
#   sudo ./scripts/install_mirror_network.sh
#   sudo ./scripts/install_mirror_network.sh --config /etc/kor35/mirror-network.env
#
# Prima di installare, copia e personalizza:
#   sudo mkdir -p /etc/kor35
#   sudo cp config/mirror/network/mirror-network.env.example /etc/kor35/mirror-network.env
#   sudo nano /etc/kor35/mirror-network.env   # EMERGENCY_WIFI_PASSPHRASE obbligatoria

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib_mirror_pi.sh
source "$SCRIPT_DIR/lib_mirror_pi.sh"

CONFIG_SRC=""
INSTALL_AUTO_MODE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --config)
      CONFIG_SRC="${2:-}"
      shift 2
      ;;
    --no-auto-mode)
      INSTALL_AUTO_MODE=0
      shift
      ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      mirror_pi_err "argomento non riconosciuto: $1"
      exit 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  mirror_pi_err "eseguire come root (sudo)"
  exit 1
fi

apt_packages=(dnsmasq hostapd iproute2 curl)
missing=()
for pkg in "${apt_packages[@]}"; do
  dpkg -s "$pkg" >/dev/null 2>&1 || missing+=("$pkg")
done
if [ "${#missing[@]}" -gt 0 ]; then
  mirror_pi_log "Installazione pacchetti: ${missing[*]}"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${missing[@]}"
fi

mkdir -p /etc/kor35 /var/lib/kor35

if [ -n "$CONFIG_SRC" ]; then
  cp "$CONFIG_SRC" /etc/kor35/mirror-network.env
elif [ ! -f /etc/kor35/mirror-network.env ]; then
  cp "$ROOT_DIR/config/mirror/network/mirror-network.env.example" /etc/kor35/mirror-network.env
  mirror_pi_warn "Creato /etc/kor35/mirror-network.env da template — imposta EMERGENCY_WIFI_PASSPHRASE"
fi

export KOR35_MIRROR_CONFIG=/etc/kor35/mirror-network.env
mirror_pi_load_config

if [ "${EMERGENCY_WIFI_PASSPHRASE:-CHANGE_ME_EMERGENCY_PSK}" = "CHANGE_ME_EMERGENCY_PSK" ]; then
  mirror_pi_warn "EMERGENCY_WIFI_PASSPHRASE non configurata in /etc/kor35/mirror-network.env"
fi

mirror_pi_render_template \
  "$ROOT_DIR/config/mirror/network/dnsmasq-event.conf.template" \
  /etc/kor35/dnsmasq-event.conf

mirror_pi_render_template \
  "$ROOT_DIR/config/mirror/network/hostapd-emergency.conf.template" \
  /etc/kor35/hostapd-emergency.conf
chmod 600 /etc/kor35/hostapd-emergency.conf

# Evita conflitto con istanza dnsmasq di sistema (solo il nostro service in modalità evento)
if [ -f /etc/dnsmasq.conf ]; then
  if ! grep -q '^# kor35-mirror-managed' /etc/dnsmasq.conf; then
    cat >>/etc/dnsmasq.conf <<'EOF'

# kor35-mirror-managed: DHCP/DNS evento gestito da kor35-mirror-dhcp-event.service
port=0
EOF
  fi
fi
systemctl disable --now dnsmasq 2>/dev/null || true

for unit in kor35-mirror-dhcp-event.service kor35-mirror-emergency-wifi.service kor35-mirror-network-mode.service; do
  src="$ROOT_DIR/config/systemd/$unit"
  dst="/etc/systemd/system/$unit"
  if [ ! -f "$src" ]; then
    mirror_pi_err "unit mancante nel repo: $src"
    exit 1
  fi
  cp "$src" "$dst"
  sed -i "s|/home/pi/kor35-replica|${KOR35_REPO_PATH}|g" "$dst"
done

if [ -f /etc/systemd/system/kor35-mirror-emergency-wifi.service ]; then
  sed -i "s|wlan0|${EMERGENCY_WIFI_INTERFACE}|g" /etc/systemd/system/kor35-mirror-emergency-wifi.service
  sed -i "s|10.42.0.1/24|${EMERGENCY_WIFI_IP}/${EMERGENCY_WIFI_CIDR}|g" /etc/systemd/system/kor35-mirror-emergency-wifi.service
fi

systemctl daemon-reload

if [ "$INSTALL_AUTO_MODE" = "1" ]; then
  systemctl enable --now kor35-mirror-emergency-wifi.service
  systemctl enable kor35-mirror-network-mode.service
else
  systemctl disable --now kor35-mirror-emergency-wifi.service 2>/dev/null || true
  mirror_pi_log "WiFi emergenza: lasciata a NetworkManager (Hotspot-Emergenza). Boot auto modalità rete disabilitato."
fi

# ddns.conf per kor35.ddns.net (HTTPS a casa) se mancante
ddns_dst="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/ddns.conf"
ddns_example="${KOR35_REPO_PATH}/config/docker/nginx-docker/nginx_conf/ddns.conf.example"
if [ ! -f "$ddns_dst" ] && [ -f "$ddns_example" ]; then
  cp "$ddns_example" "$ddns_dst"
  mirror_pi_log "Creato ddns.conf da example (richiede certificati in certs_ddns/)"
fi

mirror_pi_log "Installazione rete mirror completata."
echo ""
echo "Verifica:"
echo "  sudo ${KOR35_REPO_PATH}/scripts/mirror_network_check.sh"
echo ""
echo "Applica modalità:"
echo "  sudo ${KOR35_REPO_PATH}/scripts/mirror_network_apply_mode.sh --mode router   # ora (collegato al router)"
echo "  sudo ${KOR35_REPO_PATH}/scripts/mirror_network_apply_mode.sh --mode event    # prima dell'evento offline"
echo ""
if [ "$INSTALL_AUTO_MODE" = "1" ]; then
  echo "Al prossimo boot: kor35-mirror-network-mode.service esegue --mode auto"
fi
