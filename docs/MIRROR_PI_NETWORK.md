# Mirror Pi — reti WiFi (emergenza vs evento)

Documentazione topologia rete sul Raspberry **mirror** (`ENV=mirror`, `compose.mirror.yml` + `omada-controller`).

Runbook SSH e comandi per agenti Cursor: **`.cursor/rules/mirror-pi-ops.mdc`**.

## Accesso SSH (Cursor / PC dev / CI)

| | Produzione (master) | Mirror (Pi) |
|---|---------------------|-------------|
| Alias tipico | `kor35-prod` | `kor35-mirror` |
| Host | `www.kor35.it` | `kor35.ddns.net` |
| Porta SSH | `22` (+ proxy corkscrew in ufficio) | **`10022`** (NAT → Pi:22) |
| Utente | `deploy` | `pi` |
| Path repo | `/srv/kor35` | `/home/pi/kor35-replica` |
| Chiave PC tipica | `~/.ssh/id_docker` | `~/.ssh/id_docker` |

### Setup una tantum

1. Sul Pi, in `/home/pi/.ssh/authorized_keys`, aggiungi la pubkey del PC (`~/.ssh/id_docker.pub`).
2. Sul PC, copia `config/mirror/ssh-config.example` in `~/.ssh/config`.
3. Verifica:

```bash
ssh-keyscan -p 10022 -H kor35.ddns.net >> ~/.ssh/known_hosts
ssh kor35-mirror 'hostname'                    # → kor35
cd /path/to/kor35 && make mirror-ssh-check     # diagnostica remota
```

### Diagnostica remota (da PC, senza essere sulla LAN)

```bash
make mirror-pi-check
# equivalente: make mirror-ssh-check
```

### Aggiornare / configurare il Pi dal PC dev (Make)

Dopo commit su `main`, dal PC con SSH configurato (`kor35-mirror`, porta **10022**):

```bash
# Diagnostica
make mirror-pi-check

# Solo git pull sul Pi
make mirror-pi-pull

# Installa/aggiorna unit e template rete (preserva hotspot NetworkManager)
make mirror-pi-install-network MIRROR_NETWORK_AUTO_BOOT=0

# Cambia modalità rete
make mirror-pi-network-mode MIRROR_NETWORK_MODE=router
make mirror-pi-network-mode MIRROR_NETWORK_MODE=event

# Flusso completo: pull + install + applica modalità + check
make mirror-pi-configure MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0

# Solo pull + install (senza cambiare modalità)
make mirror-pi-update MIRROR_NETWORK_AUTO_BOOT=0
```

Sul **Pi** (locale):

```bash
make mirror-network-check ENV=mirror
sudo make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
```

### Accesso senza internet / senza NAT

| Via | Endpoint |
|-----|----------|
| WiFi emergenza | SSID `Pi_Emergenza` (NM: `Hotspot-Emergenza`) → `ssh pi@10.42.0.1` |
| LAN router | `ssh pi@192.168.1.200` (porta 22) |

**Non** committare chiavi private nel repo. Template SSH: `config/mirror/ssh-config.example`.

## Due modalità operative

| Modalità | Quando | LAN `eth0` | DHCP `192.168.100.0/24` | `www.kor35.it` |
|----------|--------|------------|---------------------------|----------------|
| **router** | Pi collegato al router di casa | DHCP dal router | **Spento** (evita conflitti) | via internet / DDNS |
| **event** | Bosco, senza WAN | Statico `192.168.100.1/24` | **Attivo** (dnsmasq) | HTTP locale + DNS → Pi |

In entrambe le modalità resta attiva la WiFi **`Pi_emergenza`** (`wlan0`, `10.42.0.1`) per staff/debug.

### Script e Make (sul Pi)

```bash
cd /home/pi/kor35-replica

# Configurazione completa (install + modalità)
sudo make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0

# Oppure passi separati:
sudo make mirror-install-network MIRROR_NETWORK_AUTO_BOOT=0
make mirror-network-check ENV=mirror
sudo make mirror-network-mode MIRROR_NETWORK_MODE=router
sudo make mirror-network-mode MIRROR_NETWORK_MODE=event
sudo make mirror-network-mode MIRROR_NETWORK_MODE=auto
```

Equivalenti script diretti:

```bash
sudo ./scripts/mirror_configure_network.sh --mode router --no-auto-mode
```

Da **PC dev** (SSH): vedi sezione «Aggiornare / configurare il Pi» sopra (`make mirror-pi-configure`, ecc.).

Prima installazione manuale env (una tantum sul Pi):

```bash
sudo mkdir -p /etc/kor35
sudo cp config/mirror/network/mirror-network.env.example /etc/kor35/mirror-network.env
sudo nano /etc/kor35/mirror-network.env   # EMERGENCY_WIFI_PASSPHRASE se usi hostapd systemd
```

Unit systemd installate da `install_mirror_network.sh`:

- `kor35-mirror-emergency-wifi.service` — hotspot `Pi_emergenza` (alternativa a NM `Hotspot-Emergenza`)
- `kor35-mirror-dhcp-event.service` — dnsmasq solo in modalità event
- `kor35-mirror-network-mode.service` — `--mode auto` al boot (opzionale; skip con `--no-auto-mode`)

## Due reti distinte (non confonderle)

| Rete | Interfaccia tipica | SSID | IP gateway | Uso |
|------|-------------------|------|------------|-----|
| **Emergenza** (on-board Pi) | `wlan0` | `Pi_Emergenza` / `Pi_emergenza` | `10.42.0.1/24` | Accesso staff al Pi **senza** infrastruttura evento (SSH, Omada UI, debug). **Non** per giocatori né console pilota. |
| **Evento** (Omada + antenne EAP) | LAN cablata Pi ↔ switch/PoE EAP; SSID broadcast dalle EAP | **`kor35-larp`** (Site Omada) | Gateway/DHCP del **Site** Omada (IP LAN del Pi su `eth0` / `en*`, **non** `10.42.0.1`) | Smartphone giocatori, Pi kiosk pilota, smartwatch. |

Stack KOR35 (nginx `:80`/`:443`) risponde su **tutte** le interfacce del Pi; i client evento devono usare l’**IP della LAN Omada**, non `10.42.0.1`.

## Cosa c’è nel repo Docker

- `config/docker/compose.mirror.yml` → servizio `omada-controller` (`network_mode: host`, porte gestione `8088`/`8043`, dati in `omada_data/` / `omada_logs/`).
- `scripts/install_mirror_network.sh` + `config/mirror/network/` → DHCP/DNS evento, hostapd emergenza, vhost nginx offline.
- `make status ENV=mirror` / `COMPOSE_PROJECT_NAME=kor35-replica` → stack KOR35 + Omada insieme.
- **Non** versionato sul Pi: Site/WLAN/DHCP in Omada (DB in `omada_data/`), PSK `Pi_emergenza` in `/etc/kor35/mirror-network.env`.

## Diagnostica mirror (comandi progetto)

```bash
cd /home/pi/kor35-replica

# Diagnostica rete + stack (consigliato)
./scripts/mirror_network_check.sh

# Stack KOR35 + Omada
make status ENV=mirror

cd config/docker
export COMPOSE_PROJECT_NAME=kor35-replica
export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror

# Omada controller
curl -sI http://127.0.0.1:8088/ | head -3
sudo ss -ulnp | grep -E '29810|29811|29812|29813'
docker compose -f compose.base.yml -f compose.mirror.yml logs omada-controller --tail 80

# Emergenza (solo staff) — NON è la rete giocatori
ip -4 addr show wlan0
iw dev wlan0 info

# LAN evento (IP che devono usare giocatori/kiosk per HTTP verso KOR35)
ip -4 addr show eth0 2>/dev/null || ip -4 addr show | grep -E 'eth|enp|end'

# KOR35 raggiungibile sull'IP evento (sostituire <IP_EVENTO>)
curl -fsS http://<IP_EVENTO>/api/healthz/ && echo KOR35_OK
```

In UI Omada (`http://<IP_PI>:8088`, anche da rete emergenza `Pi_emergenza`):

1. **Devices** → ogni EAP **Connected** (non Disconnected / Pending).
2. **Settings → Wireless → WLAN** → SSID **`kor35-larp`** → **Enabled**, radio 2.4/5 GHz attive.
3. **Settings → Wired / LAN** (o DHCP del Site) → gateway = IP LAN del Pi verso le EAP (non `10.42.0.1`).

Dal telefono: connettersi a **`kor35-larp`**, poi aprire `http://<IP_LAN_EVENTO>/` (IP da `ip addr` su `eth0`/`en*` del Pi).

## Boot offline (senza internet WAN)

1. `kor35-mirror-network-mode.service` (se installato) applica `--mode auto` → **event**.
2. `10.42.0.1` / `Pi_emergenza` resta su (hotspot on-board).
3. LAN `192.168.100.1/24` + dnsmasq → client risolvono `www.kor35.it` verso il Pi; nginx serve HTTP (`mirror-event-local.conf`).
4. Rete **giocatori** via Omada: container up → EAP adottate → WLAN `kor35-larp` → Controller IP = `192.168.100.1` (non `kor35.ddns.net`).
5. Sync DB (`kor35-mirror-db-sync`) verso master **fallisce** offline: normale, non spegne Omada.

Dopo l'evento, tornato online:

```bash
sudo ./scripts/mirror_network_apply_mode.sh --mode router
sudo systemctl start kor35-mirror-resync.service
```

## Test disconnessione (router → evento)

### Stato atteso in modalità router (a casa)

- `eth0`: solo IP DHCP router (es. `192.168.1.200/24`)
- `kor35-mirror-dhcp-event.service`: **spento**
- Sync verso master: **OK**
- WiFi staff: `Pi_Emergenza` su `10.42.0.1` (NetworkManager `Hotspot-Emergenza`)

Verifica rapida:

```bash
cd /home/pi/kor35-replica
./scripts/mirror_network_check.sh
# oppure da PC: make mirror-ssh-check
```

### Procedura di test offline (consigliata)

**Attenzione:** passando a `event`, `eth0` diventa `192.168.100.1` — la sessione SSH via `kor35.ddns.net` può cadere. Per il test tieni aperta una seconda sessione su **`Pi_Emergenza`** (`ssh pi@10.42.0.1`) o usa monitor/tastiera sul Pi.

1. **Prepara** (da SSH o locale):

```bash
cd /home/pi/kor35-replica
./scripts/mirror_network_check.sh    # modalità router, internet OK
```

2. **Simula la disconnessione WAN** (scegli una opzione):
   - **Reale:** stacca il cavo `eth0` dal router (resta collegato solo allo switch PoE Omada per le EAP), oppure
   - **A casa (lab):** lascia il cavo ma applica comunque `event` solo se `eth0` va verso switch isolato senza DHCP router sulla stessa VLAN.

3. **Attiva modalità evento:**

```bash
sudo ./scripts/mirror_network_apply_mode.sh --mode event
./scripts/mirror_network_check.sh
```

Atteso:

| Controllo | Risultato |
|-----------|-----------|
| Modalità registrata | `event` |
| `eth0` | `192.168.100.1/24` |
| DHCP evento | **ATTIVO** (`kor35-mirror-dhcp-event.service`) |
| Nginx vhost evento | attivo (`mirror-event-local.conf`) |
| Internet master | NON RAGGIUNGIBILE (normale) |
| Stack Docker + Omada | OK |

4. **Test client** (telefono o laptop sulla rete evento / `kor35-larp`):

```bash
# Sul client: DNS e HTTP (dopo associazione WiFi kor35-larp)
ping -c 2 192.168.100.1
curl -fsS http://www.kor35.it/api/healthz/
```

Se `www.kor35.it` non risolve, verifica che il client usi DNS `192.168.100.1` (dhcp da dnsmasq).

5. **Omada:** UI su `http://192.168.100.1:8088` — Controller IP = `192.168.100.1`, EAP Connected, WLAN `kor35-larp` enabled.

6. **Ripristino router** (cavo WAN/router riattaccato):

```bash
sudo ./scripts/mirror_network_apply_mode.sh --mode router
./scripts/mirror_network_check.sh
sudo systemctl start kor35-mirror-resync.service   # opzionale: riallinea DB/media post-evento
```

### Test automatico al boot (opzionale, dopo test manuale OK)

```bash
sudo ./scripts/install_mirror_network.sh --no-auto-mode   # già fatto se NM gestisce hotspot
sudo systemctl enable kor35-mirror-network-mode.service # --mode auto a ogni boot
```

Con `auto`: internet raggiungibile → `router`; altrimenti → `event`.

## Troubleshooting: `kor35-larp` visibile ma non associa

L’SSID in beacon **non** garantisce handshake WPA OK. Cause tipiche (anche se «un mese fa funzionava»):

| Causa | Dove guardare | Fix |
|--------|----------------|-----|
| **PSK cambiata** / profilo telefono vecchio | Omada → WLAN `kor35-larp` → Security | Verifica password; sul telefono *Dimentica rete* e riprova |
| **WPA3-only** / PMF obbligatorio | Omada → WLAN → Security | Prova **WPA2-PSK** (o WPA2/WPA3 mixed) per compatibilità smartphone |
| **802.1X / RADIUS** (Enterprise) | Omada → WLAN `kor35-larp` | Offline fallisce se RADIUS è remoto/cloud → usare **Personal/PSK** in evento |
| **Guest / Portal** captive | Omada → WLAN → Guest/Portal | Portal spesso richiede internet → disabilitare portal in modalità bosco |
| **Controller IP/host errato** | Omada → Settings → Controller | Deve essere **IP LAN del Pi** (`eth0`/`en*`), non `kor35.ddns.net` né hostname esterno |
| **EAP Connected ma config non applicata** | Omada → Devices | Toggle OFF/ON WLAN `kor35-larp`; power cycle EAP; *Provision* / *Sync* |
| **Deploy / upgrade Omada** (`6.1.0.19`) | `omada_logs/`, `LAST_RAN_OMADA_VER.txt` | Log controller; eventuale re-push WLAN dopo migrazione compose |

### Comandi sul Pi (da `Pi_emergenza` o SSH)

```bash
cd /home/pi/kor35-replica/config/docker
export COMPOSE_PROJECT_NAME=kor35-replica
export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror

# Log controller (errori auth / radius / wlan)
docker compose -f compose.base.yml -f compose.mirror.yml logs omada-controller --tail 200

# Log on-disk (path compose.mirror.yml)
tail -80 /home/pi/kor35-replica/omada_logs/server.log 2>/dev/null || ls -la /home/pi/kor35-replica/omada_logs/

# IP LAN evento (deve coincidere con gateway Site Omada e Controller IP)
ip -4 addr show | grep -E 'eth|enp|end' -A2

# EAP raggiungono il controller?
sudo ss -ulnp | grep -E '29810|29811|29812|29813'
```

### Test lato client

1. Telefono: **Dimentica** `kor35-larp`, riconnetti con password da Omada.
2. Prova un **secondo dispositivo** (es. laptop).
3. Se solo Enterprise: in Omada passa temporaneamente a **WPA2 Personal** con PSK nota → test associazione.

Se dopo WPA2-PSK locale e Controller IP = IP LAN il telefono associa, il regress rispetto a un mese fa è quasi certamente **Security/Portal/RADIUS** o **Controller hostname** cambiato in Site Omada (spesso durante merge monorepo o edit in UI online).

## Riferimenti errati da non usare

Non indirizzare giocatori o kiosk a `http://10.42.0.1/` salvo debug staff sulla rete emergenza. Usare l’IP/host della LAN Omada (o `kor35.ddns.net` solo **con** DNS/uplink).
