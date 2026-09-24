# Mirror Raspberry Pi — procedure

Il **mirror** (`ENV=mirror`) è un Raspberry Pi replica del master (`prod`): sync DB ~ogni 2 min, stack Docker + controller **Omada**, due modalità rete.

**Test offline con mesh Omada (passi numerati):** vedi pagina Wiki [Test sistema disconnesso](/regolamento/staff-test-offline-omada).

Path repo sul Pi: `/home/pi/kor35-replica`  
SSH pubblico: `kor35.ddns.net:10022` (alias `kor35-mirror`)

---

## Due modalità rete

| Modalità | Quando | `eth0` | DHCP `192.168.100.0/24` |
|----------|--------|--------|-------------------------|
| **router** | Pi collegato al router di casa | DHCP router (es. `192.168.1.200`) | **Spento** |
| **event** | Bosco / offline | Statico `192.168.100.1/24` | **Attivo** (dnsmasq) |

WiFi staff **sempre**: SSID `Pi_Emergenza` / `Pi_emergenza` → `10.42.0.1` (NetworkManager `Hotspot-Emergenza` **oppure** `hostapd` systemd).  
WiFi **giocatori**: `kor35-larp` via antenne Omada — **non** usare `10.42.0.1` per l'app.

---

## WiFi emergenza sempre attiva

L'hotspot staff **non** resta su da solo dopo un reboot se non è stato installato il servizio dedicato.

### Subito (hotspot giù adesso)

Da SSH (`kor35-mirror` o LAN):

```bash
cd /home/pi/kor35-replica
sudo make mirror-ensure-emergency-wifi ENV=mirror
make mirror-network-check ENV=mirror
```

**Atteso:** riga WiFi emergenza con IP `10.42.0.1/24` e stato **ATTIVO**; sul laptop compare SSID `Pi_Emergenza` o `Pi_emergenza`.

Alternativa (riapplica anche modalità router/event):

```bash
sudo make mirror-network-mode ENV=mirror MIRROR_NETWORK_MODE=router
```

### Always-on al boot (una tantum)

**Non modificare a mano** `/etc/systemd/system/kor35-mirror-*.service` sul Pi: le unit vengono copiate dal repo.

1. Password hotspot in `/etc/kor35/mirror-network.env` → `EMERGENCY_WIFI_PASSPHRASE=...` (non lasciare `CHANGE_ME_EMERGENCY_PSK`).
2. Aggiorna codice e reinstalla da repo:

```bash
cd /home/pi/kor35-replica
git pull
sudo make mirror-install-network ENV=mirror MIRROR_NETWORK_AUTO_BOOT=0
```

Solo unit systemd (dopo `git pull`, senza apt):

```bash
sudo make mirror-reinstall-units ENV=mirror
```

Da PC dev (SSH):

```bash
make mirror-pi-pull
make mirror-pi-install-network MIRROR_NETWORK_AUTO_BOOT=0
```

3. Verifica:

```bash
systemctl is-enabled kor35-mirror-ensure-emergency-wifi.service   # enabled
make mirror-network-check ENV=mirror
```

### Certificati TLS (prod → mirror)

Due domini distinti:

| Dominio | Dove vive il cert | Rinnovo |
|---------|-------------------|---------|
| `www.kor35.it` | prod (`certs/`) + copia mirror (`certs/`) | certbot su **prod** (webroot) |
| `kor35.ddns.net` | solo mirror (`certs_ddns/`) | certbot sul **Pi** (webroot) |

**Fix immediato cert scaduto su `kor35.ddns.net`** (sul Pi, con rete/router):

```bash
cd /home/pi/kor35-replica
git pull
sudo make install-mirror-ddns-tls ENV=mirror FORCE=1
# oppure solo rinnovo se automazione già installata:
sudo make mirror-renew-ddns-tls ENV=mirror FORCE=1
```

Se SSH DDNS non risponde: LAN `ssh pi@192.168.1.200` o WiFi emergenza `ssh pi@10.42.0.1`.

**Automazione prod** (dopo deploy del monorepo):

```bash
cd /srv/kor35
git pull
sudo make install-prod-tls-automation ENV=prod
# copia subito www.kor35.it sul mirror:
make sync-certs-to-mirror ENV=prod
```

**Da questa postazione dev** (relay prod → mirror, solo `www.kor35.it`):

```bash
cp config/env_templates/sync-mirror-certs.env.example .env.sync-mirror-certs

make sync-certs-prod-to-mirror
make sync-certs-prod-to-mirror DRY_RUN=1    # anteprima
```

Script: `scripts/sync_tls_certs_to_mirror.sh`, `scripts/mirror_renew_ddns_tls.sh`, `scripts/install_prod_tls_automation.sh` — reload nginx al termine.

Timer systemd: `kor35-prod-cert-sync-mirror.timer` (prod), `kor35-mirror-ddns-cert-renew.timer` (Pi).

In **modalità evento** offline: `http://www.kor35.it` (HTTP). HTTPS richiede cert aggiornati sul Pi.

**Come funziona:** a ogni boot il Pi prova prima **NetworkManager** (`Hotspot-Emergenza`); se fallisce, **hostapd** da repo se la PSK è configurata. `MIRROR_NETWORK_AUTO_BOOT=0` riguarda solo router/event automatico, non la WiFi emergenza.

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

**Procedura completa con checklist:** [Test sistema disconnesso](/regolamento/staff-test-offline-omada) (passi 1–11).

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
journalctl -u kor35-mirror-media-sync.service -n 80 --no-pager
systemctl list-timers | grep -E 'kor35-mirror-(db-sync|media-sync)'
make sync-db ENV=mirror
make sync-media          # path da .env.sync-media → master
make check-media ENV=mirror   # path rubriche mancanti su disco
```

Le **immagini rubriche** (e altri media) non viaggiano nel sync DB: solo path nel JSON + file via rsync. Timer media orario (`*:15`). Dopo upload sul master, se il Pi ha articoli senza foto: `make sync-media` subito. Se i path DB sono già corrotti (PK locale ≠ path file): `make repair-rubriche-media ENV=mirror`.

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

## Caso 7 — Chiamate vocali (TURN)

In evento i telefoni spesso **non** possono parlarsi in UDP diretto (client isolation mesh). Il relè **coturn** sul Pi riceve l’audio e lo inoltra.

- Servizio: `coturn` in `compose.mirror.yml` (`network_mode: host`).
- Porte host: **3478** UDP/TCP, relè **49160–49259** UDP.
- L’API `/api/personaggi/api/chiamate/ice-servers/` pubblica `turn:<host-app>:3478` (stesso host con cui il telefono ha aperto l’app).
- Credenziali default: `kor35turn` / `kor35turnlocal` — **cambiale** in `backend/.env.mirror`.
- **Prod** (`www.kor35.it`): coturn sul droplet con **HMAC a tempo** (`TURN_AUTH_SECRET`). Fallback se il Pi è giù: i giocatori usano la web app pubblica; l’audio passa dal VPS.

Avvio / verifica sul Pi:

```bash
cd /home/pi/kor35-replica/config/docker
export COMPOSE_PROJECT_NAME=kor35-replica
export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror
docker compose -f compose.base.yml -f compose.mirror.yml ps coturn
```

Firewall (se UFW è attivo): aprire 3478/udp, 3478/tcp e 49160:49259/udp sulla LAN evento. Non inoltrare 3478 su Internet.

Il microfono del browser richiede **HTTPS** (o localhost). In evento usare i certificati del Pi, non `http://192.168.x.x`.

### Fallback: Pi giù → www.kor35.it

Se lo stack sul Pi non parte, i giocatori usano **https://www.kor35.it** (HTTPS già ok per il microfono). Serve coturn sul droplet.

Una tantum (già eseguito sul droplet il 2026-09-08):

```bash
make prod-turn-prepare
# oppure sul server: bash scripts/prepare_prod_turn.sh
```

Scrive `TURN_AUTH_SECRET` (HMAC) e `TURN_EXTERNAL_IP` in `/srv/kor35/backend/.env.prod` e apre ufw: **3478/udp**, **3478/tcp**, **49160–49259/udp**.

Dopo il merge su `main` il deploy CI avvia `kor35_prod_coturn`. Se l’audio non parte da 4G, controllare anche il **Cloud Firewall del provider** (oltre a ufw). Coturn non è proxato da nginx.

Senza secret + porte aperte + container Up, su prod lo squillo parte e l’audio no (NAT/4G).

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
