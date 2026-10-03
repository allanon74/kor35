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

## WiFi

La **plancia dual-screen** (`deploy/raspberry-pilot-kiosk/`) non ha uno script WiFi: usa i profili NetworkManager salvati sul desktop. `kor35-larp` ha priorità, la rete di casa (Vodafone) è il ripiego.

Questa console 7" fa lo stesso, con un helper (`kor35-kiosk-wifi.sh`) perché all'accensione NetworkManager è spesso già sulla rete di casa mentre le EAP Omada comparono dopo:

| Priorità | Rete | Quando |
|----------|------|--------|
| 1 | **`kor35-larp`** | Mirror in modalità evento (bosco), stessa LAN dei giocatori |
| 2 | SSID di riserva in `/etc/kor35/kiosk-station.env` (o profilo già salvato, es. Vodafone) | Il bosco non si vede (laboratorio, casa) |
| 3 | Scelta a schermo (zenity) | Nessuna delle due risponde e `KIOSK_WIFI_PROMPT=1` |

All'avvio riprova `kor35-larp` per alcuni secondi. Se non c'è, resta sulla rete di casa. Ogni 8 secondi, se esiste un profilo `kor35-larp` (anche con underscore, `kor35_larp`) **stacca Vodafone/casa e alza quello**, anche quando lo scan da associati non elenca Omada — è lo stesso gesto della connessione manuale dal desktop. **Non riscrive la password** dei profili già salvati. Il profilo evento ha priorità 200, gli altri −100, così al boot successivo vince lui quando entrambe le reti si vedono.

Non usare `Pi_Emergenza` / `10.42.0.1` per questa console.

### Aggiornare gli script (Pi già installato, da SSH)

**Non** rilanciare `install-station-kiosk.sh`: riscrive `/etc/kor35/kiosk-station.env` e può svuotare la password.

Da una shell SSH sul Pi (utente `pi`):

```bash
REF=main
BASE="https://raw.githubusercontent.com/allanon74/kor35/${REF}/deploy/raspberry-station-kiosk"
WORKDIR=/tmp/kor35-station-kiosk
mkdir -p "$WORKDIR"
cd "$WORKDIR"
stamp=$(date +%s)
curl -fsSL -H 'Cache-Control: no-cache' -o kiosk-station.sh "${BASE}/kiosk-station.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o kor35-kiosk-wifi.sh "${BASE}/kor35-kiosk-wifi.sh?${stamp}"
curl -fsSL -H 'Cache-Control: no-cache' -o update-station-kiosk.sh "${BASE}/update-station-kiosk.sh?${stamp}"
grep -q "Scan da .* non elenca" kor35-kiosk-wifi.sh || { echo "SCRIPT VECCHIO, riprova il curl"; exit 1; }
chmod +x kiosk-station.sh kor35-kiosk-wifi.sh update-station-kiosk.sh
sudo ./update-station-kiosk.sh
```

Se `main` non ha ancora il commit, usa il branch al posto di `REF=main`, ad esempio `REF=cursor/station-kiosk-wifi-1661`.

Verifica:

```bash
nmcli -t -f NAME,TYPE,AUTOCONNECT-PRIORITY connection show
sudo /usr/local/sbin/kor35-kiosk-wifi.sh current
journalctl -u kiosk-station.service -n 40 --no-pager
curl -fsS -k https://www.kor35.it/api/healthz/ && echo OK
```

Nel log deve comparire `Passato a kor35-larp`, `Stacco` o `Già connesso a kor35-larp`. Se resta su Vodafone, spegni il kiosk, connettiti **una volta** a `kor35-larp` dal desktop (così esiste il profilo), poi riavvia il servizio: da quel momento lo script stacca da solo la casa.

Rete di riserva (es. Vodafone) se non è già in env: edita solo quelle due righe, non il file intero.

```bash
sudo nano /etc/kor35/kiosk-station.env
# KIOSK_WIFI_FALLBACK_SSID=Vodafone-XXXX
# KIOSK_WIFI_FALLBACK_PSK='password'
sudo systemctl restart kiosk-station.service
```

Il server resta `https://www.kor35.it`: in bosco il DNS del mirror lo risolve in locale.

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
