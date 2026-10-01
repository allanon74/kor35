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

| Priorità | Rete | Quando |
|----------|------|--------|
| 1 | **`kor35-larp`** | Mirror in modalità evento (bosco), stessa LAN dei giocatori |
| 2 | SSID di riserva in `/etc/kor35/kiosk-station.env` | Il bosco non si vede (laboratorio, casa) |
| 3 | Scelta a schermo (zenity) | Nessuna delle due risponde e `KIOSK_WIFI_PROMPT=1` |

Non usare `Pi_Emergenza` / `10.42.0.1` per questa console.

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

### Schermo bianco al boot

Il desktop di Raspberry Pi OS è Wayland: `:0` è Xwayland. Se Chromium parte prima del primo frame, la finestra resta bianca. Nel journal, finché non si riavvia il servizio, compare `running xinput against an Xwayland server` (il loop di `xinput` non serve su un solo pannello e su Xwayland non mappa il touch).

Un `systemctl restart kiosk-station.service` a sessione già avviata ridisegna la console. Lo script aspetta il socket Wayland e apre Chromium con `--ozone-platform=wayland`, senza `xinput`.

Per aggiornare solo lo script, senza rifare l'installazione:

```bash
sudo install -m 0755 kiosk-station.sh /usr/local/bin/kiosk-station.sh
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
