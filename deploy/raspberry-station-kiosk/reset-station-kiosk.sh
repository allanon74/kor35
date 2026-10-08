#!/usr/bin/env bash
# Azzera la console stazione e la rimette in piedi come la plancia dual-screen.
# Non cancella i profili WiFi di NetworkManager e non svuota le password in
# /etc/kor35/kiosk-station.env. Cancella solo il profilo Chromium del kiosk
# (schermo bianco da cache corrotta) e reinstalla gli script.
#
#   sudo ./reset-station-kiosk.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIOSK_USER="${KIOSK_USER:-${SUDO_USER:-pi}}"
ENV_FILE=/etc/kor35/kiosk-station.env

if [ "$(id -u)" -ne 0 ]; then
  echo "Esegui come root: sudo $0" >&2
  exit 1
fi

for f in kiosk-station.sh kor35-kiosk-wifi.sh kiosk-station.service; do
  if [ ! -f "${SCRIPT_DIR}/${f}" ]; then
    echo "Manca ${SCRIPT_DIR}/${f}" >&2
    exit 1
  fi
done
if ! grep -q "non stacco il WiFi" "${SCRIPT_DIR}/kiosk-station.sh"; then
  echo "kiosk-station.sh non è la versione nuova (manca: non stacco il WiFi)" >&2
  exit 1
fi

echo "Fermo il kiosk e Chromium"
systemctl stop kiosk-station.service 2>/dev/null || true
pkill -u "$KIOSK_USER" -f '/usr/local/bin/kiosk-station.sh' 2>/dev/null || true
pkill -u "$KIOSK_USER" -x chromium 2>/dev/null || true
pkill -u "$KIOSK_USER" -x chromium-browser 2>/dev/null || true
sleep 1

echo "Cancello il profilo Chromium del kiosk (non i WiFi)"
rm -rf "/home/${KIOSK_USER}/.config/kiosk-station"
install -d -o "$KIOSK_USER" -g "$KIOSK_USER" "/home/${KIOSK_USER}/.config/kiosk-station"

install -d /usr/local/bin /usr/local/sbin /etc/kor35
install -m 0755 "${SCRIPT_DIR}/kiosk-station.sh" /usr/local/bin/kiosk-station.sh
install -m 0755 "${SCRIPT_DIR}/kor35-kiosk-wifi.sh" /usr/local/sbin/kor35-kiosk-wifi.sh

if [ ! -f "$ENV_FILE" ]; then
  umask 077
  cat >"$ENV_FILE" <<'EOF'
PILOT_BASE_URL=https://www.kor35.it
KIOSK_START_PATH=/pilot/?screen=station&viewport=800x480
KIOSK_WIFI_MANAGE=1
KIOSK_WIFI_PRIMARY_SSID=kor35-larp
KIOSK_MODE=800x480
KIOSK_ROTATE=normal
EOF
  chown "$KIOSK_USER:$KIOSK_USER" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
else
  # Allinea l'URL a quello della plancia. Le PSK restano.
  if grep -q '^PILOT_BASE_URL=' "$ENV_FILE"; then
    sed -i 's|^PILOT_BASE_URL=.*|PILOT_BASE_URL=https://www.kor35.it|' "$ENV_FILE"
  else
    printf '\nPILOT_BASE_URL=https://www.kor35.it\n' >>"$ENV_FILE"
  fi
  if ! grep -q '^KIOSK_START_PATH=' "$ENV_FILE"; then
    printf '%s\n' 'KIOSK_START_PATH=/pilot/?screen=station&viewport=800x480' >>"$ENV_FILE"
  fi
fi

cat > /etc/sudoers.d/kor35-kiosk-wifi <<EOF
${KIOSK_USER} ALL=(root) NOPASSWD: /usr/local/sbin/kor35-kiosk-wifi.sh
EOF
chmod 440 /etc/sudoers.d/kor35-kiosk-wifi

uid="$(id -u "$KIOSK_USER")"
sed -e "s/__KIOSK_USER__/${KIOSK_USER}/g" -e "s|/run/user/1000|/run/user/${uid}|g" \
  "${SCRIPT_DIR}/kiosk-station.service" > /etc/systemd/system/kiosk-station.service

echo "Priorità WiFi: kor35-larp sopra, le altre restano (non le cancello)"
/usr/local/sbin/kor35-kiosk-wifi.sh pin || true

mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
echo "RAM totale: ${mem_kb} kB"
if [ "$mem_kb" -lt 1800000 ]; then
  echo "Sotto 2 GB: attivo zram se non c'è già."
  if ! swapon --show 2>/dev/null | grep -q zram; then
    modprobe zram || true
    if [ -b /dev/zram0 ]; then
      echo lz4 > /sys/block/zram0/comp_algorithm 2>/dev/null || true
      echo 512M > /sys/block/zram0/disksize || true
      mkswap /dev/zram0 >/dev/null 2>&1 || true
      swapon -p 100 /dev/zram0 || true
    fi
  fi
  cat > /etc/systemd/system/kor35-zram.service <<'EOF'
[Unit]
Description=KOR35 zram per la console stazione
DefaultDependencies=no
After=local-fs.target
Before=swap.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'swapon --show | grep -q zram && exit 0; modprobe zram || exit 0; [ -b /dev/zram0 ] || exit 0; echo lz4 > /sys/block/zram0/comp_algorithm 2>/dev/null || true; echo 512M > /sys/block/zram0/disksize; mkswap /dev/zram0; swapon -p 100 /dev/zram0'
ExecStop=/sbin/swapoff /dev/zram0

[Install]
WantedBy=swap.target
EOF
  systemctl enable kor35-zram.service || true
fi

need_reboot=0
runtime_dir="/run/user/${uid}"
if [ -S "${runtime_dir}/wayland-0" ] || [ -S "${runtime_dir}/wayland-1" ] \
  || pgrep -x labwc >/dev/null 2>&1 || pgrep -x wayfire >/dev/null 2>&1; then
  echo "Desktop Wayland (labwc/wayfire). La plancia che funziona usa Openbox su X11, più leggero."
  if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_wayland W1 || true
    xsession="LXDE-pi-x"
    if [ -f /usr/share/xsessions/rpd-x.desktop ] || [ -f /usr/share/wayland-sessions/rpd-labwc.desktop ]; then
      xsession="rpd-x"
    fi
    acc="/var/lib/AccountsService/users/${KIOSK_USER}"
    if [ -f "$acc" ]; then
      if grep -q '^XSession=' "$acc"; then
        sed -i "s/^XSession=.*/XSession=${xsession}/" "$acc"
      else
        printf 'XSession=%s\n' "$xsession" >>"$acc"
      fi
    fi
    need_reboot=1
    echo "Richiesto Openbox su X11 (${xsession}). Non ho installato un altro desktop."
  else
    echo "raspi-config assente. A mano: sudo raspi-config → Advanced → Wayland → X11, poi reboot."
    need_reboot=1
  fi
fi

systemctl daemon-reload
systemctl enable kiosk-station.service
if [ "$need_reboot" -eq 1 ]; then
  echo ""
  echo "Script installati. X11 parte al prossimo boot: sudo reboot"
  echo "Non ho riavviato io, così leggi questo messaggio."
else
  systemctl restart kiosk-station.service || true
  echo ""
  echo "Kiosk riavviato."
fi

echo "  script: /usr/local/bin/kiosk-station.sh"
echo "  env:    ${ENV_FILE}"
grep '^PILOT_BASE_URL=' "$ENV_FILE" || true
echo "  log:    journalctl -u kiosk-station.service -n 40 --no-pager"
echo "  prova:  curl -fsS -k https://www.kor35.it/api/healthz/ && echo OK"
