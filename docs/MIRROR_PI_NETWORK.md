# Mirror Pi — reti WiFi (emergenza vs evento)

Documentazione topologia rete sul Raspberry **mirror** (`ENV=mirror`, `compose.mirror.yml` + `omada-controller`).

## Due reti distinte (non confonderle)

| Rete | Interfaccia tipica | SSID | IP gateway | Uso |
|------|-------------------|------|------------|-----|
| **Emergenza** (on-board Pi) | `wlan0` | `Pi_emergenza` | `10.42.0.1/24` | Accesso staff al Pi **senza** infrastruttura evento (SSH, Omada UI, debug). **Non** per giocatori né console pilota. |
| **Evento** (Omada + antenne EAP) | LAN cablata Pi ↔ switch/PoE EAP; SSID broadcast dalle EAP | **`kor35-larp`** (Site Omada) | Gateway/DHCP del **Site** Omada (IP LAN del Pi su `eth0` / `en*`, **non** `10.42.0.1`) | Smartphone giocatori, Pi kiosk pilota, smartwatch. |

Stack KOR35 (nginx `:80`/`:443`) risponde su **tutte** le interfacce del Pi; i client evento devono usare l’**IP della LAN Omada**, non `10.42.0.1`.

## Cosa c’è nel repo Docker

- `config/docker/compose.mirror.yml` → servizio `omada-controller` (`network_mode: host`, porte gestione `8088`/`8043`, dati in `omada_data/` / `omada_logs/`).
- `make status ENV=mirror` / `COMPOSE_PROJECT_NAME=kor35-replica` → stack KOR35 + Omada insieme.
- **Non** versionato: hostapd/NetworkManager per `Pi_emergenza`, Site/WLAN/DHCP in Omada (DB in `omada_data/`).

## Diagnostica mirror (comandi progetto)

```bash
cd /home/pi/kor35-replica

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

- `10.42.0.1` / `Pi_emergenza` può essere su anche offline (hotspot on-board).
- La rete **evento** dipende da: Omada container up → EAP adottate → WLAN attivo → IP/gateway Site coerente **senza** default route internet.
- Sync DB (`kor35-mirror-db-sync`) verso master **fallisce** offline: normale, non spegne Omada.

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
