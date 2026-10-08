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

Il WiFi è quello della plancia dual-screen: NetworkManager tiene i profili e lo script **non stacca** la rete attuale. Se `kor35-larp` (o `kor35_larp`) è già connessa, non la tocca. Se non lo è, alza **una volta** il profilo salvato, senza riscrivere la password. Chromium parte solo quando `https://www.kor35.it/api/healthz/` risponde e si riapre se la pagina cade. Su un Pi con meno di 2 GB il reset attiva zram e, se il desktop è Wayland, passa a **Openbox su X11** (lo stesso modello della plancia, più leggero di labwc).

## Aggiornamento (Pi già installato)

**Non** rilanciare `install-station-kiosk.sh`. Da SSH:

```bash
REF=main
BASE="https://raw.githubusercontent.com/allanon74/kor35/${REF}/deploy/raspberry-station-kiosk"
WORKDIR=/tmp/kor35-station-kiosk
mkdir -p "$WORKDIR" && cd "$WORKDIR"
stamp=$(date +%s)
curl -fsSL -H 'Cache-Control: no-cache' -o kiosk-station.sh "${BASE}/kiosk-station.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o kor35-kiosk-wifi.sh "${BASE}/kor35-kiosk-wifi.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o reset-station-kiosk.sh "${BASE}/reset-station-kiosk.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o update-station-kiosk.sh "${BASE}/update-station-kiosk.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o kiosk-station.service "${BASE}/kiosk-station.service?${stamp}"
grep -q "non stacco il WiFi" kiosk-station.sh || { echo "SCRIPT VECCHIO, riprova il curl"; exit 1; }
chmod +x kiosk-station.sh kor35-kiosk-wifi.sh reset-station-kiosk.sh update-station-kiosk.sh
sudo ./reset-station-kiosk.sh
```

Se il reset chiede X11, `sudo reboot`. Poi `journalctl -u kiosk-station.service -n 40 --no-pager`: devono comparire `modello plancia: non stacco il WiFi` e `Server ok`.

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

Su un Pi già installato non rilanciare l'installer (riscrive l'env e può cancellare la PSK). Aggiorna solo gli script:

```bash
sudo install -m 0755 kiosk-station.sh /usr/local/bin/kiosk-station.sh
sudo install -m 0755 kor35-kiosk-wifi.sh /usr/local/sbin/kor35-kiosk-wifi.sh
sudo systemctl restart kiosk-station.service
```

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
