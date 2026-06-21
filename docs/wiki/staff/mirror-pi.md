# Mirror Raspberry Pi — procedure

Il **mirror** (`ENV=mirror`) è un Raspberry Pi replica del master (`prod`): sync DB ~ogni 2 min, stack Docker + controller **Omada**, due modalità rete.

Path repo sul Pi: `/home/pi/kor35-replica`  
SSH pubblico: `kor35.ddns.net:10022` (alias `kor35-mirror`)

---

## Due modalità rete

| Modalità | Quando | `eth0` | DHCP `192.168.100.0/24` |
|----------|--------|--------|-------------------------|
| **router** | Pi collegato al router di casa | DHCP router (es. `192.168.1.200`) | **Spento** |
| **event** | Bosco / offline | Statico `192.168.100.1/24` | **Attivo** (dnsmasq) |

WiFi staff **sempre**: SSID `Pi_Emergenza` / `10.42.0.1` (NetworkManager `Hotspot-Emergenza`).  
WiFi **giocatori**: `kor35-larp` via antenne Omada — **non** usare `10.42.0.1` per l'app.

---

## Caso 1 — A casa (collegato al router)

**Obiettivo:** sync verso master, niente DHCP locale in conflitto.

```bash
# Sul Pi
cd /home/pi/kor35-replica
sudo make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
make mirror-network-check ENV=mirror
```

**Da PC dev**

```bash
make mirror-pi-configure MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
make mirror-pi-check
```

**Atteso:** `eth0` solo IP router, internet OK, sync timer attivo, DHCP evento spento.

---

## Caso 2 — Prima dell'evento (offline / bosco)

**Obiettivo:** LAN `192.168.100.1`, DHCP+DNS locale, `www.kor35.it` → Pi, Omada + `kor35-larp`.

⚠️ La SSH via DDNS può cadere. Tieni aperta una sessione su **`Pi_Emergenza`** (`ssh pi@10.42.0.1`).

```bash
sudo make mirror-network-mode ENV=mirror MIRROR_NETWORK_MODE=event
make mirror-network-check ENV=mirror
```

**Da PC dev**

```bash
make mirror-pi-network-mode MIRROR_NETWORK_MODE=event
```

**Verifiche**

- `eth0` → `192.168.100.1/24`
- `kor35-mirror-dhcp-event.service` attivo
- `curl http://www.kor35.it/api/healthz/` da client su `kor35-larp` (DNS `192.168.100.1`)
- Omada UI: `http://192.168.100.1:8088` — Controller IP = `192.168.100.1`

---

## Caso 3 — Dopo l'evento (tornato online)

```bash
sudo make mirror-network-mode ENV=mirror MIRROR_NETWORK_MODE=router
make mirror-resync-after-event ENV=mirror
make mirror-network-check ENV=mirror
```

**Da PC dev**

```bash
make mirror-pi-network-mode MIRROR_NETWORK_MODE=router
```

---

## Caso 4 — Prima installazione rete (una tantum)

```bash
sudo mkdir -p /etc/kor35
sudo cp config/mirror/network/mirror-network.env.example /etc/kor35/mirror-network.env
sudo nano /etc/kor35/mirror-network.env   # PSK emergenza se usi hostapd systemd
sudo make mirror-install-network MIRROR_NETWORK_AUTO_BOOT=0
```

Oppure da PC dopo deploy: `make mirror-pi-update MIRROR_NETWORK_AUTO_BOOT=0`

---

## Caso 5 — Diagnostica problemi

```bash
make mirror-network-check ENV=mirror          # sul Pi
make mirror-pi-check                          # da PC
make status ENV=mirror
make logs ENV=mirror
```

**Sync**

```bash
journalctl -u kor35-mirror-db-sync.service -n 80 --no-pager
make sync-db ENV=mirror
```

**Omada / WLAN `kor35-larp`**

- Devices → EAP Connected
- WLAN `kor35-larp` → WPA2-PSK (non solo WPA3/RADIUS offline)
- Controller IP = IP LAN Pi (`192.168.100.1` in evento), non `kor35.ddns.net`

**Stack Docker**

```bash
cd /home/pi/kor35-replica/config/docker
export COMPOSE_PROJECT_NAME=kor35-replica
export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror
docker compose -f compose.base.yml -f compose.mirror.yml ps
```

---

## Caso 6 — Deploy CI / aggiornamento codice

Il deploy GitHub Actions aggiorna il repo sul Pi (`git reset --hard origin/main`).  
Non copiare script a mano via SCP.

Dopo merge su `main`, da PC:

```bash
make mirror-pi-configure MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
```

---

## Accesso SSH

| Via | Comando |
|-----|---------|
| Internet | `ssh kor35-mirror` (porta **10022**) |
| LAN router | `ssh pi@192.168.1.200` |
| Emergenza | WiFi `Pi_Emergenza` → `ssh pi@10.42.0.1` |

Template: `config/mirror/ssh-config.example`

---

## Riferimenti repo

- `docs/MIRROR_PI_NETWORK.md`
- `.cursor/rules/mirror-pi-ops.mdc`
- `config/docker/SYNC.md`
- `make help` (sezione Mirror Pi)
