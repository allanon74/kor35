# Console pilota — kiosk dual-screen (Raspberry)

Runbook per il **serverino dedicato** alla plancia: due monitor (grande + barra touch larga e bassa), Chromium in kiosk, **nessun** Docker sul device.

| Monitor | Ruolo | URL |
|---------|--------|-----|
| **Grande** (max risoluzione) | Stato nave, eventi, gauge | `/pilot/?screen=status` |
| **Piccolo / touch** (barra) | Plancia comandi touch | `/pilot/?screen=control` |

Stack KOR35 (API + `/pilot/`) gira sul **mirror** in modalità evento o su **prod** — il kiosk è solo browser.

Script di riferimento: `deploy/raspberry-pilot-kiosk/` (installazione con `install-kiosk-pi.sh`).

---

## File e servizi sul Pi kiosk

| Path | Contenuto |
|------|-----------|
| `/etc/kor35/kiosk.env` | URL server, layout monitor, touch |
| `/usr/local/bin/kiosk-master.sh` | Avvio Chromium + xrandr + touch |
| `kiosk-master.service` | Avvio automatico al boot |
| `/etc/kor35/NO_KIOSK` | Se esiste, il kiosk non parte (debug desktop) |

```bash
systemctl status kiosk-master.service
journalctl -u kiosk-master.service -f
```

---

## Schermi invertiti (status e control scambiati)

Il rilevamento automatico assegna **grande → status**, **piccolo → control**. Se i ruoli sono al contrario:

### Soluzione rapida (consigliata)

```bash
sudo nano /etc/kor35/kiosk.env
```

Aggiungi o imposta:

```bash
KIOSK_SWAP_SCREENS=1
```

Poi:

```bash
sudo systemctl restart kiosk-master.service
```

### Output HDMI fissi (hardware noto)

Se `auto` sbaglia i connettori, usa nomi espliciti (tipico installazione KOR35: barra touch su `HDMI-1`, grande su `HDMI-2`):

```bash
KIOSK_DETECT_OUTPUTS=fixed
KIOSK_STATUS_OUTPUT=HDMI-2
KIOSK_CONTROL_OUTPUT=HDMI-1
KIOSK_STATUS_MODE=1920x1200
KIOSK_CONTROL_MODE=1920x440
```

Elenco connettori e risoluzioni attuali:

```bash
export DISPLAY=:0
xrandr --query
```

Riavvio servizio dopo ogni modifica a `kiosk.env`.

---

## Touch sul monitor sbagliato

Il touch deve stare sulla **barra control** (schermo piccolo). Lo script mappa il dispositivo con `xinput map-to-output`.

### Verifica dispositivi touch

```bash
export DISPLAY=:0
xinput list | grep -iE 'ilitek|touch|pen'
```

### Configurazione in `kiosk.env`

```bash
# Output X11 della barra touch (stesso di CONTROL)
KIOSK_TOUCH_OUTPUT=HDMI-1

# Nome esatto del device (default ILITEK)
KIOSK_TOUCH_DEVICE=ILITEK ILITEK-TOUCH

# Se il nome non basta, usa l'id numerico da xinput list
# KIOSK_TOUCH_XINPUT_ID=6
```

### Mappa manuale (test immediato, senza reboot)

```bash
export DISPLAY=:0
xinput map-to-output <ID_TOUCH> HDMI-1
```

Sostituisci `<ID_TOUCH>` con l'id da `xinput list` e `HDMI-1` con l'output della barra.

Il servizio ripete la mappatura ogni ~45 s; se dopo il boot il touch «salta» sul grande, controlla che `KIOSK_TOUCH_OUTPUT` coincida con `KIOSK_CONTROL_OUTPUT`.

### Touch assente o non risponde

- Cavo USB del touch collegato al Pi (non al monitor grande).
- `sudo apt install xinput` se mancante (reinstall: `deploy/raspberry-pilot-kiosk/install-kiosk-pi.sh`).
- Riavvia solo il kiosk: `sudo systemctl restart kiosk-master.service`.

---

## WiFi e connessione al server

### Rete corretta

| Rete | Uso |
|------|-----|
| **`kor35-larp`** (Omada, LAN evento `192.168.100.x`) | **Console pilota + smartphone giocatori** |
| `Pi_Emergenza` / `10.42.0.1` | Solo emergenza staff / SSH debug — **non** per il kiosk in gioco |

Il kiosk deve raggiungere `https://www.kor35.it` (in bosco il DNS locale del mirror risolve lo stesso hostname verso il Pi server).

### Test connettività dal Pi kiosk

```bash
curl -fsS https://www.kor35.it/api/healthz/ && echo OK
curl -fsS https://www.kor35.it/api/pilot/console-enabled/
```

Atteso: `healthz` → 200; `console-enabled` → `"enabled": true` sul mirror/prod evento.

### Schermo bianco / «offline» / pagina non carica

1. Verifica WiFi: `nmcli dev wifi list` — connesso a **`kor35-larp`**?
2. Ping verso gateway LAN evento (es. `192.168.100.1` sul mirror).
3. Controlla URL in `/etc/kor35/kiosk.env`:
   ```bash
   PILOT_BASE_URL=https://www.kor35.it
   ```
   Evita IP vecchi (`192.168.1.200`) se non hai impostato un fallback esplicito.
4. Log: `journalctl -u kiosk-master.service -n 80 --no-pager`
5. Sul **server** (mirror): `make status ENV=mirror` e `PILOT_CONSOLE_ENABLED=true` nel `.env`.

### Cambiare server (lab / mirror diverso)

```bash
sudo nano /etc/kor35/kiosk.env
# PILOT_BASE_URL=https://www.kor35.it
sudo systemctl restart kiosk-master.service
```

Per chiedere l'URL a ogni boot: `KOR35_KIOSK_PROMPT_URL=1`.

---

## Chromium / finestre

### Una finestra nera, l'altra OK

```bash
sudo systemctl restart kiosk-master.service
```

Se persiste, elimina lock profili e riavvia:

```bash
rm -f ~/.config/kiosk-status/Singleton* ~/.config/kiosk-control/Singleton*
sudo systemctl restart kiosk-master.service
```

### Uscire dal kiosk per debug (tastiera + mouse)

```bash
sudo touch /etc/kor35/NO_KIOSK
sudo systemctl stop kiosk-master.service
# … debug con desktop …
sudo rm /etc/kor35/NO_KIOSK
sudo systemctl start kiosk-master.service
```

### Certificato HTTPS / avviso sicurezza

Lo script kiosk usa `--ignore-certificate-errors` per eventi offline con cert locale. Se compare comunque un blocco, verifica che il mirror abbia i cert aggiornati (`make sync-certs-prod-to-mirror` da PC dev).

---

## Layout e risoluzioni strane

Barra tagliata o finestre sovrapposte:

```bash
export DISPLAY=:0
xrandr --query
```

Conferma che i due output siano **affiancati** (`side_by_side`), non duplicati (mirror). In `kiosk.env`:

```bash
KIOSK_LAYOUT=side_by_side
```

Modalità consigliate per hardware tipico: status `1920x1200`, control `1920x440`. Se il monitor piccolo non supporta la modalità, lo script prova `--auto`.

---

## Reinstallazione pulita

Da cartella `deploy/raspberry-pilot-kiosk/` sul Pi:

```bash
sudo systemctl disable --now kor35-kiosk.service 2>/dev/null || true
sudo ./install-kiosk-pi.sh --base-url https://www.kor35.it
```

Checklist rapida: `deploy/raspberry-pilot-kiosk/TEST-CHECKLIST-10MIN.md`.

---

## Riferimenti

- `deploy/raspberry-pilot-kiosk/README.md` — installazione e variabili
- `deploy/raspberry-pilot-kiosk/kiosk.env.example` — template completo `kiosk.env`
- `docs/CONSOLE_PILOTA_RUNBOOK.md` — API e stack server
- Wiki [Test offline — mesh Omada](/regolamento/staff-test-offline-omada) — rete evento e IP LAN
