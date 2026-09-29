# KOR35 — kiosk stazione 800×480 (Raspberry Pi 4)

Client leggero per il **pannello touch 7" 800×480**: un solo Chromium, niente Docker e niente clone del monorepo.

| Macchina | Ruolo |
|----------|--------|
| **Server** (mirror in modalità bosco, oppure prod) | API + `/pilot/` |
| **Questo Pi** | Schermo di scelta, poi QR di login |

All'avvio il browser apre `/pilot/?screen=station&viewport=800x480` (riquadro fisico 800×480):

1. Tre pulsanti: **Ingegneria**, **Scientifica** e **Comunicazioni**. Comunicazioni compare spenta finché non la abiliti in Console di bordo.
2. Dopo il tocco compare il QR. Il telefono del giocatore deve avere la statistica impostata nello staff (default ingegneria `0IN > 0`, scientifica `0SC > 0`, comunicazioni `0CO > 0`).
3. La console entra nel layout compatto, pensato per 800×480. Ingegneria e scientifica usano le schede; comunicazioni mostra i colori di allarme.

Il WiFi prova prima **`kor35-larp`** (mesh Omada, modalità evento / bosco). Se quella rete non c'è, usa l'SSID di riserva salvato oppure chiede a schermo quale rete usare.

## Installazione

Raspberry Pi OS **con desktop** e login automatico sulla sessione grafica (il servizio aspetta `graphical.target`).

```bash
scp -r deploy/raspberry-station-kiosk pi@<IP>:/tmp/
ssh pi@<IP>
cd /tmp/raspberry-station-kiosk
sudo ./install-station-kiosk.sh --base-url https://www.kor35.it --wifi-psk 'PASSWORD_KOR35_LARP'
```

Rete di casa già nota, usata solo se il bosco non si vede:

```bash
sudo ./install-station-kiosk.sh \
  --base-url https://www.kor35.it \
  --wifi-psk 'PASSWORD_LARP' \
  --fallback-ssid Casa \
  --fallback-psk 'PASSWORD_CASA'
```

Utente desktop diverso da `pi`:

```bash
sudo ./install-station-kiosk.sh --user giorgio --base-url https://www.kor35.it
```

### File sul Pi

| Path | Contenuto |
|------|-----------|
| `/usr/local/bin/kiosk-station.sh` | Chromium + schermo + scelta WiFi |
| `/usr/local/sbin/kor35-kiosk-wifi.sh` | Connessione NetworkManager (via sudo) |
| `/etc/systemd/system/kiosk-station.service` | Avvio al boot |
| `/etc/kor35/kiosk-station.env` | URL, SSID, PSK (permessi `600`) |
| `/etc/kor35/NO_KIOSK` | Se esiste, il kiosk non parte |

La PSK non va nel git. Il file di esempio è `kiosk-station.env.example`.

## Verifica

```bash
systemctl status kiosk-station.service
journalctl -u kiosk-station.service -n 80 --no-pager
curl -fsS -k https://www.kor35.it/api/healthz/ && echo OK
curl -fsS -k https://www.kor35.it/api/pilot/station/consoles/
```

Sul server, in staff → runtime console, abilita **Console Ingegneria** e **Console Scientifica** e controlla le sigle di accesso.

## Uscire dal kiosk

```bash
sudo touch /etc/kor35/NO_KIOSK
sudo systemctl stop kiosk-station.service
# debug desktop, poi:
sudo rm /etc/kor35/NO_KIOSK
sudo systemctl start kiosk-station.service
```

## Rotazione del pannello

In `/etc/kor35/kiosk-station.env`:

```bash
KIOSK_ROTATE=right
```

Valori: `normal`, `left`, `right`, `inverted`. Poi `sudo systemctl restart kiosk-station.service`.

## Non confondere

| Device | Cartella | Schermi |
|--------|----------|---------|
| Plancia doppio HDMI | `deploy/raspberry-pilot-kiosk/` | status + control |
| Questo Pi 7" | `deploy/raspberry-station-kiosk/` | ingegneria, scientifica o comunicazioni |

Runbook staff: `docs/wiki/staff/console-stazione-kiosk.md`.
