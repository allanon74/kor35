# KOR35 Pilotaggio Kiosk Dual Screen (Raspberry Pi)

Client **leggero**: solo Chromium su due HDMI. **Nessun** Docker, **nessun** clone del monorepo necessario.

| Macchina | Ruolo |
|----------|--------|
| **Server** (prod o mirror Pi) | Stack Docker, API, `/pilot/` |
| **Kiosk** (questo device) | Due finestre browser fisse |

## Layout schermi (automatico)

| Schermo | URL | Note |
|---------|-----|------|
| **Più grande** (max risoluzione) | `/pilot/?screen=status` | Stato nave |
| **Più piccolo** | `/pilot/?screen=control` | Plancia comandi |

- Rilevamento via `xrandr` (area pixel).
- Profili Chromium **separati** → le finestre **non** si scambiano URL/sessione.
- Watchdog riavvia solo la finestra morta, senza invertire i ruoli.

## Server predefinito

**`https://www.kor35.it`** — in bosco (mirror in modalità `event`) il DNS locale risolve lo stesso hostname verso il Pi.

All'avvio il kiosk prova `https` e `http` su `/api/healthz/`.

## Installazione (sul Pi kiosk)

Copia **solo** questa cartella sul device (USB, `scp`, ecc.):

```bash
scp -r deploy/raspberry-pilot-kiosk pi@<IP_KIOSK>:/tmp/
ssh pi@<IP_KIOSK>
cd /tmp/raspberry-pilot-kiosk
sudo ./install-kiosk-pi.sh
```

Con dialogo URL all'avvio:

```bash
sudo ./install-kiosk-pi.sh --prompt-url
```

URL custom una tantum:

```bash
sudo ./install-kiosk-pi.sh --base-url https://www.kor35.it
```

### File installati

| Path | Contenuto |
|------|-----------|
| `/usr/local/bin/kiosk-master.sh` | Script principale |
| `/etc/systemd/system/kiosk-master.service` | Avvio automatico |
| `/etc/kor35/kiosk.env` | `PILOT_BASE_URL`, `KOR35_KIOSK_PROMPT_URL` |

## Configurazione successiva

```bash
sudo nano /etc/kor35/kiosk.env
# PILOT_BASE_URL=https://www.kor35.it
# KOR35_KIOSK_PROMPT_URL=1   # chiedi URL a ogni boot

sudo systemctl restart kiosk-master.service
```

## Verifica

```bash
systemctl status kiosk-master.service
journalctl -u kiosk-master.service -f
curl -fsS https://www.kor35.it/api/healthz/
curl -fsS https://www.kor35.it/pilot/?screen=status -o /dev/null -w '%{http_code}\n'
```

## Rete

- Kiosk su WiFi **`kor35-larp`** (stessa LAN dei giocatori).
- **Non** usare `Pi_Emergenza` / `10.42.0.1` per la console.

## Migrazione da installazione precedente

Se avevi `kor35-kiosk.service` o URL hardcoded (`192.168.1.200`):

```bash
sudo systemctl disable --now kor35-kiosk.service 2>/dev/null || true
sudo ./install-kiosk-pi.sh
```

Checklist collaudo: `TEST-CHECKLIST-10MIN.md`.
