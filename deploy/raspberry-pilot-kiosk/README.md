# KOR35 Pilotaggio Kiosk Dual Screen (Raspberry Pi)

Obiettivo:
- Schermo 1 (HDMI principale): solo stato nave/eventi (`/pilot/?screen=status`)
- Schermo 2 touchscreen 1920x440: plancia comandi (`/pilot/?screen=control`)

## Requisiti minimi consigliati
- Raspberry Pi 4B (2GB+). Consigliato 4GB.
- Raspberry Pi OS Lite/Full 64bit.
- Chromium.
- Rete locale verso server EDGE (o stack locale docker).

## Nota hardware
- Una microSD di buona qualita e sufficiente per boot e runtime kiosk.
- Pi Zero: sconsigliato per dual-screen HDMI + UI web reattiva.
- Pi 4B e adatto al carico previsto.

## 1) Setup base (host Raspberry)
```bash
sudo apt update
sudo apt install -y xserver-xorg x11-xserver-utils xinit openbox chromium-browser unclutter
```

## 2) Copia script kiosk
```bash
sudo mkdir -p /opt/kor35-kiosk
sudo cp deploy/raspberry-pilot-kiosk/start-kiosk.sh /opt/kor35-kiosk/start-kiosk.sh
sudo chmod +x /opt/kor35-kiosk/start-kiosk.sh
```

## 3) Service systemd
```bash
sudo cp deploy/raspberry-pilot-kiosk/kor35-kiosk.service /etc/systemd/system/kor35-kiosk.service
sudo systemctl daemon-reload
sudo systemctl enable kor35-kiosk.service
sudo systemctl start kor35-kiosk.service
```

## 4) URL e display
Modifica in `/opt/kor35-kiosk/start-kiosk.sh`:
- `PILOT_BASE_URL` con URL locale raggiungibile (es. `http://10.42.0.1`)
- mapping output display (`HDMI-1` e `HDMI-2`) secondo `xrandr`.

## 5) Test rapido
- URL per profilo Docker WSL:
  - `dev-home`: `http://127.0.0.1:8080/pilot/?screen=status` e `http://127.0.0.1:8080/pilot/?screen=control`
  - `dev-office`: `http://127.0.0.1:8081/pilot/?screen=status` e `http://127.0.0.1:8081/pilot/?screen=control`
- In rete Edge usa `http://<ip-edge>/pilot/?screen=...`.
- Esegui checklist completa: `deploy/raspberry-pilot-kiosk/TEST-CHECKLIST-10MIN.md`.

## Docker-first (servizi backend/frontend)
Eseguire stack KOR35 nel modo standard del progetto (`docker compose ...`).
Il Raspberry kiosk funge da terminale UI; il motore tick resta lato server (`pilot_tick --loop --interval 5`).
