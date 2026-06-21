# Test sistema disconnesso (mesh Omada)

Procedura **passo-passo** per simulare l’evento in bosco: niente internet verso il master, rete giocatori su **Omada** (`kor35-larp`), app KOR35 servita dal **mirror** sul Pi.

**Prerequisito:** stack mirror già installato (`ENV=mirror`), unit rete installate, EAP adottate in Omada. Per installazione iniziale vedi [Mirror Pi — procedure](/regolamento/staff-mirror-pi).

---

## Cosa stai testando (in breve)

| Componente | Online (casa) | Offline (evento) |
|------------|---------------|------------------|
| Modalità rete Pi | `router` — `eth0` DHCP router | `event` — `eth0` = `192.168.100.1/24` |
| Internet verso master | Sì (sync DB ~2 min) | **No** (sync fallisce: normale) |
| WiFi staff | `Pi_Emergenza` → `10.42.0.1` | Stesso (sempre attivo) |
| WiFi giocatori | `kor35-larp` (Omada EAP) | Stesso — **questo** è il test principale |
| App / API | `www.kor35.it` via internet o LAN | `www.kor35.it` risolto dal Pi (DNS locale) |

**Non confondere le reti:** smartphone giocatori e kiosk pilota usano la LAN Omada (`192.168.100.x`), **non** `10.42.0.1` (solo emergenza staff).

---

## Hardware minimo per il test

1. **Raspberry mirror** con stack Docker up (`backend`, `frontend`, `omada-controller`, …).
2. **Switch PoE** (o injector) + almeno **un’antenna EAP** Omada già adottata.
3. **Cavo `eth0` del Pi** verso lo switch PoE (LAN evento), **non** verso il router di casa durante il test offline.
4. **Telefono** (e opzionale laptop) per associarsi a `kor35-larp`.
5. **Laptop staff** con WiFi `Pi_Emergenza` (o monitor/tastiera sul Pi) — **obbligatorio** come piano B SSH.

---

## Prima del test (a casa, ancora online)

Esegui tutto **prima** di staccare il router: serve sync dati e verifica baseline.

### Passo 1 — Stack e sync

```bash
# Sul Pi (o da PC: make mirror-pi-check)
cd /home/pi/kor35-replica
make status ENV=mirror
make mirror-network-check ENV=mirror
```

**Atteso:** container `kor35_mirror_*` e `omada_controller` **Up**; modalità rete **`router`**; sync verso master **OK** (ultimo pull recente).

Se il DB è vecchio, da PC o sul Pi (con internet):

```bash
make sync-db-full ENV=mirror
# opzionale media:
make sync-media ENV=mirror
```

### Passo 2 — Omada pronta (mentre hai ancora internet)

Apri UI Omada: `http://<IP_PI_LAN>:8088` (a casa spesso `http://192.168.1.200:8088`).

| Controllo | Dove in Omada | Valore atteso |
|-----------|---------------|---------------|
| EAP adottate | Devices | Stato **Connected** (non Pending) |
| SSID giocatori | Settings → Wireless → WLAN | **`kor35-larp`** — **Enabled** |
| Sicurezza WLAN | WLAN → Security | **WPA2-PSK** (Personal), **no** RADIUS/cloud-only |
| Portal captive | WLAN → Guest/Portal | **Disabilitato** (in bosco non c’è WAN) |
| Controller IP | Settings → Controller | IP LAN del Pi su `eth0` (in evento: **`192.168.100.1`**) |

> Se il Controller IP punta a `kor35.ddns.net` o un hostname esterno, correggilo **ora**: offline le EAP non raggiungono il controller.

### Passo 3 — Modalità router confermata

```bash
sudo make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
make mirror-network-check ENV=mirror
```

**Atteso:** `eth0` solo IP del router; servizio `kor35-mirror-dhcp-event` **inattivo**.

### Passo 4 — Apri sessione di emergenza (prima di passare a `event`)

La SSH via `kor35.ddns.net:10022` **cade** quando `eth0` diventa `192.168.100.1`.

1. Sul laptop: connetti WiFi **`Pi_Emergenza`** (password in `/etc/kor35/mirror-network.env` se configurata).
2. Apri terminale: `ssh pi@10.42.0.1`
3. Tieni questa sessione **aperta** per tutto il test.

---

## Test offline — sequenza esatta

### Passo 5 — Stacca la WAN (simula bosco)

Scegli **una** opzione:

| Opzione | Azione |
|---------|--------|
| **A — Reale (consigliata)** | Scollega `eth0` dal router; collega `eth0` **solo** allo switch PoE Omada |
| **B — Lab a casa** | `eth0` già sullo switch isolato, senza DHCP del router sulla stessa VLAN |

Non serve spegnere il Pi.

### Passo 6 — Attiva modalità evento

**Sul Pi** (sessione `10.42.0.1` o tastiera locale):

```bash
cd /home/pi/kor35-replica
sudo make mirror-network-mode ENV=mirror MIRROR_NETWORK_MODE=event
make mirror-network-check ENV=mirror
```

**Atteso dopo il check:**

| Controllo | Risultato |
|-----------|-----------|
| Modalità registrata | `event` |
| `eth0` | `192.168.100.1/24` |
| `kor35-mirror-dhcp-event.service` | **active** |
| Ping internet / master | **fallisce** (normale) |
| Docker + Omada | container **Up** |

Equivalente da **PC dev** (se SSH DDNS ancora viva nel breve istante prima del cambio IP):

```bash
make mirror-pi-network-mode MIRROR_NETWORK_MODE=event
```

### Passo 7 — Verifica Omada e mesh

Da laptop su `Pi_Emergenza` o da telefono già su `kor35-larp`:

1. Browser → `http://192.168.100.1:8088`
2. **Devices** → ogni EAP **Connected**
3. **WLAN `kor35-larp`** → Enabled, 2.4 + 5 GHz
4. Se EAP **Disconnected**: power cycle antenna; in Omada *Provision* / toggle WLAN

Log rapidi sul Pi:

```bash
cd /home/pi/kor35-replica/config/docker
export COMPOSE_PROJECT_NAME=kor35-replica
export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror
docker compose -f compose.base.yml -f compose.mirror.yml ps
docker compose -f compose.base.yml -f compose.mirror.yml logs omada-controller --tail 50
```

### Passo 8 — Test client giocatore (telefono)

1. **Dimentica** la rete `kor35-larp` sul telefono (impostazioni WiFi) e riconnetti con la PSK da Omada.
2. Verifica IP: il telefono deve essere su `192.168.100.x` (DHCP Omada o dnsmasq del Site — non `10.42.x`).
3. Apri browser o app:

```text
http://www.kor35.it/
```

oppure, se il DNS non risolve ancora:

```text
http://192.168.100.1/
```

4. Check API:

```bash
# Da terminale sul telefono (Termux) o da laptop su kor35-larp:
curl -fsS http://www.kor35.it/api/healthz/
```

**Atteso:** risposta OK; login giocatore; QR / scheda personaggio funzionano con **dati già sincronizzati** (nessun write verso prod finché sei offline).

### Passo 9 — Test kiosk pilota (opzionale)

Sul Pi kiosk sulla rete Omada, `PILOT_BASE_URL` deve puntare all’IP LAN evento, **non** `10.42.0.1`:

```bash
# Su kiosk: /etc/kor35/kiosk.env
PILOT_BASE_URL=http://192.168.100.1
```

Riavvia servizio kiosk e verifica console su `http://192.168.100.1/pilot/`.

### Passo 10 — Checklist finale offline

| # | Verifica | OK? |
|---|----------|-----|
| 1 | Telefono associa `kor35-larp` | ☐ |
| 2 | `curl http://www.kor35.it/api/healthz/` | ☐ |
| 3 | App carica scheda / wiki / QR | ☐ |
| 4 | Omada: tutte le EAP Connected | ☐ |
| 5 | Sync timer fallisce senza crash stack (`journalctl -u kor35-mirror-db-sync -n 20`) | ☐ |

---

## Fine test — tornare online

### Passo 11 — Ripristina router e resync

1. Ricollega `eth0` al router (o ripristina uplink WAN).
2. Sul Pi:

```bash
cd /home/pi/kor35-replica
sudo make mirror-network-mode ENV=mirror MIRROR_NETWORK_MODE=router
make mirror-network-check ENV=mirror
make mirror-resync-after-event ENV=mirror
```

Da PC:

```bash
make mirror-pi-network-mode MIRROR_NETWORK_MODE=router
```

**Atteso:** `eth0` DHCP router; sync verso master **OK**; eventuali modifiche fatte offline sul mirror propagate al master (LWW su `updated_at`).

---

## Test al boot (dopo che il manuale è OK)

Per non rifare i passi a ogni accensione in bosco:

```bash
sudo make mirror-install-network MIRROR_NETWORK_AUTO_BOOT=0   # già fatto in install
sudo systemctl enable kor35-mirror-network-mode.service       # --mode auto al boot
```

Con **`auto`**: se c’è internet → `router`; se no → `event`.

---

## Problemi frequenti

| Sintomo | Causa probabile | Fix |
|---------|-----------------|-----|
| SSH DDNS persa dopo `event` | Normale | Usa `Pi_Emergenza` → `ssh pi@10.42.0.1` |
| `kor35-larp` visibile ma non associa | WPA3-only, RADIUS, portal | Omada → WPA2-PSK, no portal, no RADIUS remoto |
| App non carica su telefono | Client su `10.42.x` o DNS sbagliato | Solo rete Omada; DNS `192.168.100.1` |
| EAP Disconnected | Controller IP errato / cablaggio | Controller IP = `192.168.100.1`; cavo Pi ↔ switch PoE |
| Dati vecchi in app | Sync non fatto prima del test | A casa: `make sync-db-full ENV=mirror` poi ripeti test |

Dettaglio troubleshooting WLAN: sezione Omada in [Mirror Pi — procedure](/regolamento/staff-mirror-pi) (Caso 5).

---

## Riferimenti repo

- `docs/MIRROR_PI_NETWORK.md` — topologia completa
- `deploy/raspberry-pilot-kiosk/README.md` — URL kiosk offline
- `config/docker/SYNC.md` — sync master ↔ mirror
