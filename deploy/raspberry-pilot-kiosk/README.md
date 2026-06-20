# KOR35 Pilotaggio Kiosk Dual Screen (Raspberry Pi)

## Architettura (due Raspberry)

| Macchina | Ruolo |
|----------|--------|
| **Pi mirror** (`kor35-replica`) | Stack Docker (web app + API + `/pilot/`) + Omada WiFi |
| **Pi kiosk** (questo setup) | Solo Chromium su due HDMI; **non** esegue Docker |

Il kiosk deve raggiungere il mirror sulla **rete evento Omada** (IP LAN del Pi su `eth0`/`en*`, **non** `10.42.0.1`). Vedi `docs/MIRROR_PI_NETWORK.md`.

Obiettivo display:
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

## 1) Installazione rapida (sul Pi kiosk, da clone repo o copia cartella)

```bash
cd /path/to/kor35-replica   # oppure scp della cartella deploy/raspberry-pilot-kiosk
sudo ./deploy/raspberry-pilot-kiosk/install-kiosk-pi.sh --pilot-base-url http://<IP_LAN_EVENTO>
```

## 2) URL mirror (offline evento)

- **Pi kiosk → Pi mirror**: `PILOT_BASE_URL=http://<IP_LAN_EVENTO>` in `/etc/kor35/kiosk.env` (rete Omada/EAP)
- **Smartphone giocatori**: WiFi **`kor35-larp`**, poi `http://<IP_LAN_EVENTO>/` — **non** `Pi_emergenza` / `10.42.0.1`
- **Solo staff/debug**: `Pi_emergenza` → `10.42.0.1` (wlan0 on-board, accesso emergenza al Pi)
- **Non usare offline**: `https://kor35.ddns.net` (DNS assente)

Dopo modifica env:

```bash
sudo systemctl restart kor35-kiosk.service
```

## 3) Display

Adatta in `/opt/kor35-kiosk/start-kiosk.sh` gli output `HDMI-1` / `HDMI-2` secondo `xrandr`.

## 5) Test rapido
- URL per profilo Docker WSL:
  - `dev-home`: `http://127.0.0.1:8080/pilot/?screen=status` e `http://127.0.0.1:8080/pilot/?screen=control`
  - `dev-office`: `http://127.0.0.1:8081/pilot/?screen=status` e `http://127.0.0.1:8081/pilot/?screen=control`
- In rete Edge usa `http://<ip-edge>/pilot/?screen=...`.
- Esegui checklist completa: `deploy/raspberry-pilot-kiosk/TEST-CHECKLIST-10MIN.md`.

## Docker-first (servizi backend/frontend)
Eseguire stack KOR35 nel modo standard del progetto (`docker compose ...`).
Il Raspberry kiosk funge da terminale UI; il motore tick resta lato server (`pilot_tick --loop --interval 5`).
