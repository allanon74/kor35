# Console stazione — kiosk 800×480 (Raspberry Pi 4)

Pannello touch **7" 800×480** per **Ingegneria**, **Scientifica** e **Comunicazioni**. Un solo schermo, Chromium a tutto schermo, nessun Docker sul device.

Lo stack (API e `/pilot/`) gira sul **mirror in modalità bosco** oppure su **prod**. Il Pi è solo un browser.

Script: `deploy/raspberry-station-kiosk/` (`sudo ./install-station-kiosk.sh`).

---

## Cosa vede il giocatore

1. Tre pulsanti: **Ingegneria**, **Scientifica** e **Comunicazioni**. Sotto, la sigla richiesta (quella dei settaggi di pilotaggio, default `0IN > 0`, `0SC > 0` e `0CO > 0`). Comunicazioni resta spenta finché non la abiliti in Console di bordo.
2. Dopo il tocco, il QR di login. Lo smartphone deve essere già nell'app, con un personaggio che ha quella statistica.
3. La console si apre a schede, nel riquadro 800×480.

| Pulsante | URL | Ticket | Abilità |
|----------|-----|--------|---------|
| Ingegneria | `/pilot/?screen=compattatore&viewport=800x480` | ruolo `ingegneria` | sigla staff ingegneria (`compattatore_stat_accesso_sigla`) |
| Scientifica | `/pilot/?screen=scientifica&viewport=800x480` | ruolo `scientifica` | sigla staff scientifica |
| Comunicazioni | `/pilot/?screen=comunicazioni&viewport=800x480` | ruolo `comunicazioni` | sigla staff comunicazioni (`comunicazioni_stat_accesso_sigla`, default `0CO`) |

Pagina di scelta: `/pilot/?screen=station&viewport=800x480`.

Le schede ingegneria sono Motore, Quantico, Fuel, Stiva. Quelle scientifiche sono Spettro, Scan, Matrice, Interventi. Comunicazioni è una griglia di colori (giallo, rosso, nero, blu, ambra, viola, bianco, crociera) nello stesso riquadro 800×480: il testo di stato sta su una riga, i pulsanti riempiono il resto. **Scelta** torna al menu, **Esci** chiude il login.

Se nello staff il login della console è spento, dopo il pulsante l'accesso è automatico e il QR non compare.

---

## Rete e schermo

La plancia dual-screen non ha un loop che stacca il WiFi: NetworkManager tiene `kor35-larp`, e Chromium apre `https://www.kor35.it` quando il server risponde. Questa console ora fa lo stesso.

- Se `kor35-larp` è già connessa, lo script **non la tocca**.
- Se non lo è, alza **una volta** il profilo salvato (anche `kor35_larp`). Non riscrive la password e non fa `connection down`.
- Chromium parte solo dopo che `/api/healthz/` risponde. Se la pagina cade, lo chiude e riprova.
- Il reset, se trova labwc o wayfire, passa a **Openbox su X11** (`raspi-config nonint do_wayland W1`) e chiede un reboot. È il desktop della plancia, e pesa meno di Wayland. Non installare un altro ambiente.
- L'URL è forzato a `https://www.kor35.it`, come la plancia. In bosco il DNS del mirror lo risolve in locale.

Non usare `Pi_Emergenza` / `10.42.0.1` per questa console.

### Azzerare e ripartire (SSH, utente pi)

**Non** rilanciare `install-station-kiosk.sh`: riscriverebbe le password. `reset-station-kiosk.sh` e `update-station-kiosk.sh` cancellano solo il profilo Chromium del kiosk e reinstallano gli script.

```bash
REF=main
BASE="https://raw.githubusercontent.com/allanon74/kor35/${REF}/deploy/raspberry-station-kiosk"
WORKDIR=/tmp/kor35-station-kiosk
mkdir -p "$WORKDIR"
cd "$WORKDIR"
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

Se lo script dice di passare a X11:

```bash
sudo reboot
```

Poi:

```bash
curl -fsS -k https://www.kor35.it/api/healthz/ && echo OK
journalctl -u kiosk-station.service -n 40 --no-pager
```

Nel log deve comparire `modello plancia: non stacco il WiFi` e `Server ok`.

### Memoria e desktop

Lo schermo bianco, con l'icona WiFi accesa, è spesso Chromium senza RAM oppure una finestra finita su Xwayland. La plancia che funziona usa **X11**, non Wayland.

Se `free -h` mostra meno di 2 GB totali (Pi 4 da 1 GB):

- il reset attiva **zram** (512 MB di swap compressa)
- sotto i 250 MB liberi Chromium parte senza GPU
- non serve un altro desktop: Openbox su X11, come la plancia, è già più leggero. Wayland + labwc + Chromium sul pannello 7" è il caso che avvisa «poca memoria»

Non installare un ambiente più pesante. Se dopo il reboot X11 il pannello è ancora bianco, in `/etc/kor35/kiosk-station.env` aggiungi `KIOSK_DISABLE_GPU=1` e `sudo systemctl restart kiosk-station.service`.

---

## Installazione sul Pi

Raspberry Pi OS con desktop e autologin grafico.

```bash
sudo ./install-station-kiosk.sh --base-url https://www.kor35.it --wifi-psk 'PASSWORD'
```

Con rete di riserva:

```bash
sudo ./install-station-kiosk.sh \
  --wifi-psk 'PASSWORD_LARP' \
  --fallback-ssid NomeRete \
  --fallback-psk 'PASSWORD_RETE'
```

| Path | Ruolo |
|------|--------|
| `/etc/kor35/kiosk-station.env` | URL, SSID, password WiFi |
| `/usr/local/bin/kiosk-station.sh` | Avvio Chromium |
| `kiosk-station.service` | Boot |
| `/etc/kor35/NO_KIOSK` | Se il file esiste, il kiosk non parte |

```bash
systemctl status kiosk-station.service
journalctl -u kiosk-station.service -n 80 --no-pager
curl -fsS -k https://www.kor35.it/api/pilot/station/consoles/
```

Atteso: `ingegneria.enabled`, `scientifica.enabled` e `comunicazioni.enabled` a true quando le tre console sono accese nello staff e `PILOT_CONSOLE_ENABLED` è attivo sul server.

### Pannello ruotato

```bash
# in /etc/kor35/kiosk-station.env
KIOSK_ROTATE=right
sudo systemctl restart kiosk-station.service
```

### Debug desktop

```bash
sudo touch /etc/kor35/NO_KIOSK
sudo systemctl stop kiosk-station.service
sudo rm /etc/kor35/NO_KIOSK
sudo systemctl start kiosk-station.service
```

---

## Staff

In runtime console abilita le tre console e, se serve, cambia la sigla. Il QR della stazione usa quella sigla: un personaggio con solo navigazione (`0PI`) non sblocca l'ingegneria. Comunicazioni si accende con il flag in Console di bordo.

I link rapidi stanno in dashboard staff → **Link app**: pagina di selezione, Compattatore, Scientifica e Comunicazioni (anche nel riquadro 800×480 del Pi).

Anteprima layout sul PC (senza backend), finestra del browser larga:

`/pilot/?screen=station&viewport=800x480&preview=layout`

Poi i pulsanti aprono il QR dimostrativo. Per la console piena:

`/pilot/?screen=compattatore&viewport=800x480&preview=layout`

`/pilot/?screen=scientifica&viewport=800x480&preview=layout`

`/pilot/?screen=comunicazioni&viewport=800x480&preview=layout`

Aggiungi `&tab=stiva` o `&tab=matrice` per aprire una scheda.

---

## Non confondere

La plancia di **navigazione** (doppio HDMI, status + control) resta `deploy/raspberry-pilot-kiosk/`. Questo Pi non la sostituisce.

Come si gioca la **Console Scientifica** (spettro, scan, matrice, interventi) è nella pagina **Console Scientifica — utilizzo**.
