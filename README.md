# kor35
sito kor35

## Indice

- [Panoramica rapida](#panoramica-rapida)
- [Struttura repository](#struttura-repository)
- [Deploy sicuro (GitHub Actions)](#deploy-sicuro-github-actions)
- [OTA smartwatch (T-Watch)](#ota-smartwatch-t-watch)
- [Wear OS app (distribuzione APK)](#wear-os-app-distribuzione-apk)
- [Backup DB (produzione)](#backup-db-produzione)
- [Sviluppo locale in WSL](#sviluppo-locale-in-wsl)
- [Setup Da Zero: Deploy Automatico GitHub](#setup-da-zero-deploy-automatico-github)
- [Setup Ambienti Di Sviluppo (prima di `make`)](#setup-ambienti-di-sviluppo-prima-di-make)
- [Appendice: Comandi rapidi quotidiani](#appendice-comandi-rapidi-quotidiani)
- [Transizione post-merge (docker → main)](#transizione-post-merge-docker--main)
- [Git: merge in `main` e riallineamento branch](#git-merge-in-main-e-riallineamento-branch)

## Panoramica rapida

Monorepo KOR35 con architettura:
- `backend/` Django + DRF + Channels
- `frontend/` React/Vite
- `config/docker/` compose base + override ambiente
- `scripts/` automazione operativa (`up/down/logs/status/sync`, merge Git verso `main`, riallineamento branch)

Profili ambiente supportati:
- `dev-home`
- `dev-office`
- `mirror`
- `prod`

Documentazione estesa:
- runbook ambienti docker: `docs/DOCKER_ENVIRONMENTS_RUNBOOK.md`
- setup WSL rapido: `docs/WSL_DEV_SETUP.md`
- roadmap migrazione monorepo: `docs/MONOREPO_MIGRATION.md`

## Struttura repository

Struttura root attesa:

- `backend/`
- `frontend/`
- `config/`
- `docs/`
- `scripts/`
- `extra/`

Dettagli:
- `config/docker/compose.base.yml` + `compose.<env>.yml`
- `config/env_templates/*.env.example` template env backend per profilo
- `scripts/use_env_backend.sh` per inizializzare `backend/.env.<profilo>`

## Git: merge in `main` e riallineamento branch

Due script nella root repo (`./scripts/…`) per workflow tipici dopo lavoro su un branch (es. `test`) e aggiornamenti diretti su `main`.

### `merge_current_into_main.sh`

Merge del **branch corrente** dentro **`main`** locale, con conferma interattiva.

| Comando | Effetto |
|--------|--------|
| `./scripts/merge_current_into_main.sh` | `git checkout main` → `git merge <branch-precedente>` → **`git push origin main`** → torni sul branch di partenza |
| `./scripts/merge_current_into_main.sh --no-push` | Stesso merge **senza** push (solo locale) |
| `./scripts/merge_current_into_main.sh --push` | Esplicito: uguale al default |

Prerequisiti: working tree pulita; non essere già su `main`; branch locale `main` presente. In caso di **conflitto sul merge**, lo script si interrompe mentre sei su `main`: risolvi e completa a mano. Dopo merge/push riusciti viene eseguito di nuovo `git checkout` sul branch iniziale.

Aiuto: `./scripts/merge_current_into_main.sh --help`

### `realign_branch_to_main.sh`

Aggiorna il **branch corrente** con quanto presente su **`origin/main`** (utile se `main` è avanti perché qualcuno ha pushato senza passare dal tuo branch).

| Comando | Effetto |
|--------|--------|
| `./scripts/realign_branch_to_main.sh` | `git fetch` → **`git merge origin/main`** nel branch corrente |
| `./scripts/realign_branch_to_main.sh --hard` | **`git reset --hard origin/main`**: il branch locale diventa identico a `origin/main` (perdi commit non presenti su `origin/main`; chiede conferma, salvo `--yes`) |

Opzioni: `--remote <nome>` (default `origin`), `--main <branch>` (default `main`). Richiede working tree pulita.

## Deploy sicuro (GitHub Actions)

Workflow principale: `.github/workflows/deploy.yml`
I workflow sotto `frontend/.github/workflows/` sono stati **rimossi** (non erano caricati da GitHub nel monorepo, ma generavano confusione).

- Trigger automatico su `push` in `main` + trigger manuale (`workflow_dispatch`) con:
  - `ref`: branch/tag/SHA da rilasciare
  - `run_migrations`: abilita/disabilita migrate
  - `force_frontend_build`: se `true`, esegue sempre `npm ci` / `npm run build` in CI e lo `rsync` degli statici anche senza commit in `frontend/` (utile se `react_build` sul server è corrotto o disallineato)
- Fasi:
  - `guard-main-ref`: blocca deploy se `ref != main`
  - `build-frontend`: se in questo deploy sono cambiati file sotto `frontend/`, su **GitHub Actions** esegue `npm ci` e `npm run build` e salva `dist/` come artifact (Node sul runner, **non sul server**)
  - `production-deploy`: opzionale `rsync` di `dist/` in `config/docker/nginx-docker/react_build/` sul server, poi SSH con `git pull` e `docker compose` (`compose.base + compose.prod`). Prima di `rsync` viene fermato `frontend` e la cartella `react_build` viene riassegnata all’utente SSH via `docker run … chown` (evita errori «Permission denied» e SPA con chunk 404 se i file erano stati scritti come root dal volume Docker).
  - `mirror-deploy`: stesso `rsync` verso il Pi (se il frontend è stato buildato), poi SSH con compose mirror (stesso pre-step permessi).
  - Ripristino manuale permessi sul server (es. dopo un deploy fallito a metà): da `/srv/kor35` eseguire `scripts/fix_react_build_permissions.sh` (rileva la root) oppure `scripts/fix_react_build_permissions.sh <path-monorepo> prod|mirror` (l’utente deve poter usare `docker` o `sudo -n docker`).
  - Se il sito è «bianco» dopo deploy: sul server `scripts/verify_react_build_consistency.sh <path-assoluto-a/nginx-docker/react_build>` controlla che ogni `src`/`href` in `index.html` abbia il file corrispondente; se fallisce, permessi/rsync o cache (browser / CDN).
  - Su produzione non usare `npm` sul server per servire il sito: `make restart ENV=prod` usa `--skip-frontend-build` e riavvia solo il container frontend. Se serve riparare permessi su `frontend/node_modules` (es. dopo un `npm` lanciato come root): `scripts/fix_frontend_dir_permissions.sh` dalla root del monorepo.

**Scelta deploy frontend (decisione progetto):** il build React avviene **in CI** (runner Ubuntu), poi gli statici vanno sul server con `rsync` **solo quando `frontend/` è cambiato**. Così il server di produzione resta minimale: **Docker + git**, senza installare npm/Node in produzione. Sul server **senza** npm usa `./scripts/setup_wsl_pi_like.sh --skip-frontend-build` (crea le directory; `react_build` la popoli con deploy CI o copiando `dist/` da un PC con Node). In locale (es. WSL) puoi usare lo script senza skip se hai `npm` installato.

Rollback manuale: `.github/workflows/rollback.yml`

- Trigger manuale con `rollback_ref` (SHA/tag/branch)
- Ripristina codice, installa dipendenze, `collectstatic`, restart servizi, healthcheck

### Secrets richiesti

Produzione (obbligatori):
- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_SSH_KEY`

Produzione (opzionali ma consigliati):
- `SERVER_SSH_PORT` (default `22`)
- `SERVER_PROJECT_PATH` (default `/srv/kor35`)
- `PROD_COMPOSE_PROJECT_NAME` (default `kor35-prod`)
- `PRODUCTION_HEALTHCHECK_URL` (fortemente consigliato)

Mirror Raspberry (obbligatori):
- `MIRROR_SERVER_HOST`
- `MIRROR_SERVER_USER`
- `MIRROR_SERVER_SSH_KEY`

Mirror Raspberry (opzionali):
- `MIRROR_SERVER_SSH_PORT` (default **`10022`** — NAT pubblico verso Pi:22)
- `MIRROR_ROOT_PATH` (default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_PATH` (fallback path monorepo, default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_REPO_URL` (usato solo bootstrap se il path non esiste)
- `MIRROR_COMPOSE_PROJECT_NAME` (default `kor35-replica`)
- `MIRROR_HEALTHCHECK_URL` (fortemente consigliato)

**Allineamento path:** `MIRROR_ROOT_PATH` e `MIRROR_BACKEND_PATH` devono indicare la **stessa root del monorepo** sul Pi (dove esistono `config/docker/compose.base.yml` e `backend/.env.mirror`). Se imposti solo uno dei due, ora anche lo **rsync** del frontend usa la stessa priorità dello step SSH (`ROOT_PATH` → `BACKEND_PATH` → default).

**Legacy:** il vecchio workflow solo-frontend in `frontend/.github/workflows/` è stato **rimosso**; il deploy è solo `.github/workflows/deploy.yml` in root.

### Mirror / Docker: 502 Bad Gateway (dopo deploy o aggiornamenti)

Cause tipiche:

1. **IP del container cambiato** — Nginx con `proxy_pass http://backend:8000` risolve `backend` all’avvio e può restare sull’IP vecchio se solo il backend viene ricreato → *Connection refused*. **Fix definitivo in repo:** in `nginx_conf/common_locations.snippets` usiamo **`resolver 127.0.0.11`** (DNS Docker) e **`proxy_pass http://$variabile`** così il nome viene risolto di nuovo periodicamente (`valid=10s`).
2. **Upstream non ancora pronto** — healthcheck Compose + `depends_on: condition: service_healthy` sul `frontend`.
3. **Crash / migrate / timeout** — log `docker compose logs backend`.

Altri accorgimenti:

- **`GET /api/healthz/`** — risposta `ok` senza DB (healthcheck Docker e monitoraggio).
- **Docker Compose** (`config/docker/compose.base.yml` + override ambiente): healthcheck su `db`, `redis`, `backend`, `daphne`; Nginx parte quando backend e daphne sono **healthy**; Gunicorn `--timeout 120`.
- **GitHub Actions** (`mirror-deploy`): dopo `docker compose up` esegue **`nginx -s reload`** sul servizio `frontend` (rete di sicurezza oltre al resolver dinamico).
- **Nginx**: timeout proxy verso backend e WebSocket.

**Sul Pi, dopo un aggiornamento:**

1. Attendi fino a ~2 minuti al primo avvio (import Django lento su ARM).
2. `docker compose ps` — verifica che `backend` e `daphne` siano `healthy`, non solo `Up`.
3. `docker compose logs backend --tail 80` — errori migrazioni, `ALLOWED_HOSTS`, DB, Redis.
4. Migrazioni pendenti: `docker compose exec backend python manage.py migrate --noinput`.
5. Test rapido: `curl -sk https://localhost/api/healthz/` (dal Pi) o dall’esterno con il tuo host.

**Workflow deploy:** imposta `MIRROR_HEALTHCHECK_URL` sull’URL pubblico di `/api/healthz/` così la pipeline fallisce se il mirror non è davvero servibile.

### Nota importante

Il deploy è intenzionalmente **main-only**: anche da `workflow_dispatch` viene rifiutato qualsiasi `ref` diverso da `main`.

## OTA smartwatch (T-Watch)

Firmware OTA T-Watch 2021:

- sorgente firmware locale (versionato su GitHub ma escluso dai server in deploy): `extra/local-artifacts/lilygo-twatch-2021/`
- artefatti OTA (versionati su GitHub ma esclusi dai server in deploy): `extra/ota-artifacts/lilygo-twatch-2021/`
- artefatto OTA deployato verso `react_build/watch-ota/...`: `extra/ota-artifacts/lilygo-twatch-2021/firmware.bin`
- script release: `scripts/release_watch_ota.sh`

### Flusso operativo standard

1. Compila e prepara il binario OTA:

```bash
cd /home/django/progetti/kor35
./scripts/release_watch_ota.sh
```

2. Verifica che esista:

```bash
ls -lh extra/ota-artifacts/lilygo-twatch-2021/firmware.bin
```

3. Commit/push su `main`.

4. Il workflow `.github/workflows/deploy.yml` copia automaticamente `firmware.bin` su:
   - production (`react_build/watch-ota/lilygo-twatch-2021/firmware.bin`)
   - mirror raspberry (`react_build/watch-ota/lilygo-twatch-2021/firmware.bin`)

### Note

- Se `firmware.bin` non e' presente, il deploy fa **skip** dello step OTA senza fallire.
- Lo script usa PlatformIO CLI (`pio`) e l'env `ttgo-t-watch` (override con `PIO_ENV=...`).

## Wear OS app (distribuzione APK)

Distribuzione APK Wear OS:

- sorgente app locale (versionato su GitHub ma escluso dai server in deploy): `extra/local-artifacts/wearos-kor35/`
- artefatti APK (versionati su GitHub ma esclusi dai server in deploy): `extra/ota-artifacts/wearos-kor35/`
- script release APK: `scripts/release_wearos_apk.sh`

### Flusso operativo standard

1. Compila e prepara l'APK:

```bash
cd /home/django/progetti/kor35
./scripts/release_wearos_apk.sh
```

2. Verifica che esista:

```bash
ls -lh extra/ota-artifacts/wearos-kor35/app-release.apk
```

3. Commit/push su `main`.

4. Il workflow `.github/workflows/deploy.yml` copia automaticamente `app-release.apk` su:
   - production (`react_build/watch-apps/wearos-kor35/app-release.apk`)
   - mirror raspberry (`react_build/watch-apps/wearos-kor35/app-release.apk`)

5. Nella web app, se il personaggio ha `watch_enabled`, in sezione Devices compare il pulsante download Wear OS.

### Setup WSL per build APK (Gradle)

Se lavori da WSL e il progetto Wear e' sotto `/home/...`, usa tool Linux (non Gradle/JDK Windows).

1. Installa prerequisiti:

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk zip unzip curl
```

2. Installa SDKMAN + Gradle moderno:

```bash
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install gradle 8.7
gradle -v
```

3. Genera il wrapper nel progetto Wear:

```bash
cd /home/django/progetti/kor35/extra/local-artifacts/wearos-kor35
gradle wrapper --gradle-version 8.7
```

4. Esegui release APK:

```bash
cd /home/django/progetti/kor35
./scripts/release_wearos_apk.sh
```

Note:
- Se Android Studio e' installato su Windows, non usare JDK Windows per build Gradle su progetto WSL.
- Se lo script segnala problemi download bootstrap Gradle (403/proxy), genera prima `gradlew` con i comandi sopra.

## Backup DB (produzione)

Nel monorepo è disponibile un dump giornaliero PostgreSQL su file con rotazione **bisettimanale** (14 giorni).

- **Script**: `scripts/backup_db_daily.sh`
- **Make target**: `make backup-db ENV=prod`
- **systemd**: `config/systemd/kor35-db-backup.service` + `config/systemd/kor35-db-backup.timer`

Esecuzione manuale:

```bash
cd /srv/kor35
make backup-db ENV=prod
```

Directory e retention configurabili:
- `KOR35_DB_BACKUP_DIR` (default: `/var/backups/kor35/db`)
- `KOR35_DB_BACKUP_RETENTION_DAYS` (default: `14`)

Installazione timer systemd (sul server):

```bash
sudo mkdir -p /var/backups/kor35/db
sudo chmod 700 /var/backups/kor35/db

sudo cp /srv/kor35/config/systemd/kor35-db-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kor35-db-backup.timer
```

Log ultimo run:

```bash
sudo journalctl -u kor35-db-backup.service -n 200 --no-pager
```

## Transizione post-merge (docker → main)

Sequenza pensata quando **il branch `docker` non è ancora in `main`**, il **server di produzione** è già stato portato al layout Docker (monorepo sul branch `docker`, es. `www.kor35.it` risponde) e il **Raspberry** è ancora allo **stadio precedente** (es. solo `docker-compose.yml` in root del clone, non `config/docker/compose.base.yml` + `compose.mirror.yml`).

### Stato tipico prima del merge

| Ambiente | Situazione |
|----------|------------|
| **Git** | `main` = vecchio deploy (Apache/venv o incompleto); `docker` = monorepo + `config/docker` + workflow CI aggiornato |
| **Produzione** | Clone già aggiornato in gran parte da `docker`, DNS (es. `www.kor35.it`) punta al nuovo host |
| **Pi** | Clone `~/kor35-replica`, stack avviato con compose **legacy**; dati Omada in `/home/pi/kor35-replica/omada_data` e `omada_logs` (bind mount attuali) |

Nel repo, `compose.mirror.yml` monta Omada su **`../../omada_data`** e **`../../omada_logs`** (root monorepo), **stessi path** del Pi attuale: al passaggio al compose del monorepo **non** serve spostare i dati Omada.

### Fase A — Repository e GitHub

1. **Merge** del branch `docker` in `main` (PR consigliata, review di `deploy.yml` e `compose.*`). In alternativa da terminale, con branch di lavoro checked out: `./scripts/merge_current_into_main.sh` (merge + push `main` di default; vedi [Git: merge in `main` e riallineamento branch](#git-merge-in-main-e-riallineamento-branch)).
2. **Push** su `origin/main`: se usi solo PR/Merge su GitHub, verifica che `main` remoto sia aggiornato; se usi `./scripts/merge_current_into_main.sh` senza `--no-push`, il push è già incluso.
3. Il workflow legacy in **`frontend/.github/workflows/`** è stato **rimosso** dal repo; il deploy ufficiale è solo **`.github/workflows/deploy.yml`** in root.
4. **Secrets**: compila o aggiorna secondo la tabella **«Riepilogo secrets»** in questa sezione e la tabella **4.1** in *Setup Da Zero*; in particolare `SERVER_PROJECT_PATH` e `PRODUCTION_HEALTHCHECK_URL` per produzione, `MIRROR_*` per il Pi.

### Fase B — Server di produzione (dopo il merge)

Esegui come utente deploy (es. `deploy`):

```bash
cd /srv/kor35   # o il path in SERVER_PROJECT_PATH
git fetch origin
git checkout main
git pull origin main

cd config/docker
export KOR35_BACKEND_ENV_FILE="$(pwd)/../../backend/.env.prod"
docker compose -f compose.base.yml -f compose.prod.yml build --pull backend daphne
docker compose -f compose.base.yml -f compose.prod.yml up -d
docker compose -f compose.base.yml -f compose.prod.yml exec -T backend python manage.py migrate --noinput
docker compose -f compose.base.yml -f compose.prod.yml exec -T backend python manage.py collectstatic --noinput
```

Verifica:

```bash
curl -fsS https://www.kor35.it/api/healthz/
docker compose -f compose.base.yml -f compose.prod.yml ps
```

**Errori comuni:** `backend/.env.prod` mancante o symlink `backend/.env` errato; certificati TLS in `nginx-docker/certs/`; primo avvio lento (healthcheck backend).

### Fase C — Raspberry Pi (da layout precedente a monorepo)

1. **Backup opzionale** (consigliato prima del primo `switch`):
   ```bash
   sudo tar -czf ~/backup-omada-pre-merge-$(date +%Y%m%d).tar.gz -C /home/pi/kor35-replica omada_data omada_logs
   ```
2. **Ferma** lo stack **senza** ` -v` (non cancellare volumi/bind mount):
   ```bash
   cd /home/pi/kor35-replica
   docker compose down
   ```
   (o il comando che usi oggi; l’importante è **non** usare `docker compose down -v`.)
3. **Aggiorna** il repo alla `main` con merge:
   ```bash
   cd /home/pi/kor35-replica
   git fetch origin
   git checkout main
   git pull origin main
   ```
4. **Env mirror:** `backend/.env.mirror` da template e symlink `backend/.env` → `.env.mirror` se usi comandi locali.
5. **Avvio stack monorepo** (Omada e KOR35 nello stesso progetto compose):
   ```bash
   cd /home/pi/kor35-replica/config/docker
   export KOR35_BACKEND_ENV_FILE=/home/pi/kor35-replica/backend/.env.mirror
   docker compose -f compose.base.yml -f compose.mirror.yml up -d --build
   ```
6. Verifica: `docker compose ps`, interfaccia Omada (porte `8088` / `8043` come da compose), `curl` su healthcheck mirror.

Se il vecchio `docker-compose.yml` in root non serve più, rinominalo (es. `docker-compose.yml.legacy`) per evitare confusione; **non** cancellare `omada_data` / `omada_logs`.

### Fase D — CI e validazione end-to-end

1. Da GitHub: **Actions → Safe Release Deploy → Run workflow** (workflow_dispatch), `run_migrations` come preferisci.
2. Controlla che **production-deploy** e **mirror-deploy** siano verdi.
3. Se fallisce lo **rsync** mirror: allinea `MIRROR_ROOT_PATH` e `MIRROR_BACKEND_PATH` alla stessa root (`/home/pi/kor35-replica`).

### Riepilogo secrets (inserire / modificare in GitHub)

Usa **Settings → Secrets and variables → Actions**. Valori da adattare ai tuoi host/path.

**Produzione**

| Secret | Obbligatorio | Valore tipico / note |
|--------|--------------|----------------------|
| `SERVER_HOST` | Sì | IP o hostname raggiungibile dal runner (es. host del nuovo server) |
| `SERVER_USER` | Sì | Utente SSH (es. `deploy`) |
| `SERVER_SSH_KEY` | Sì | Chiave **privata** OpenSSH per la CI |
| `SERVER_SSH_PORT` | No | `22` se standard |
| `SERVER_PROJECT_PATH` | Forte consiglio | `/srv/kor35` (o path reale del clone) |
| `PROD_COMPOSE_PROJECT_NAME` | No | Es. `kor35-prod` (deve coincidere con `docker compose ls` sul server) |
| `PRODUCTION_HEALTHCHECK_URL` | Forte consiglio | `https://www.kor35.it/api/healthz/` |

**Mirror (Pi)**

| Secret | Obbligatorio | Valore tipico / note |
|--------|--------------|----------------------|
| `MIRROR_SERVER_HOST` | Sì | Hostname/IP del Pi (es. `kor35.ddns.net`) |
| `MIRROR_SERVER_USER` | Sì | Es. `pi` |
| `MIRROR_SERVER_SSH_KEY` | Sì | Chiave privata CI per il Pi |
| `MIRROR_SERVER_SSH_PORT` | No | **`10022`** (NAT pubblico → Pi:22) |
| `MIRROR_ROOT_PATH` | Forte consiglio | `/home/pi/kor35-replica` (root monorepo) |
| `MIRROR_BACKEND_PATH` | No | Stesso valore di `MIRROR_ROOT_PATH` se usi solo un path |
| `MIRROR_COMPOSE_PROJECT_NAME` | No | `kor35-replica` (come `docker compose ls` sul Pi) |
| `MIRROR_HEALTHCHECK_URL` | Forte consiglio | `https://kor35.ddns.net/api/healthz/` (o URL pubblico del mirror) |
| `MIRROR_BACKEND_REPO_URL` | Solo bootstrap | URL `git clone` se la cartella su Pi non esiste ancora |

Dopo la transizione, un **push su `main`** con modifiche a `frontend/` esegue build + rsync + deploy; senza modifiche frontend solo deploy backend via SSH.

## Sviluppo locale in WSL

Per setup completo backend + frontend + Postgres locale + sync pull-only dal Master:

- vedi `docs/WSL_DEV_SETUP.md`
- stack Docker "Pi-like" WSL: `scripts/setup_wsl_pi_like.sh`, poi `scripts/up_wsl_pi_like.sh` / `scripts/down_wsl_pi_like.sh`
- media pull-only (rsync): `scripts/sync_media_pull_wsl_pi_like.sh`
- stato migrazione monorepo: `docs/MONOREPO_MIGRATION.md`
- env per ambiente: `config/env_templates/README.md`
- runbook docker ambienti: `docs/DOCKER_ENVIRONMENTS_RUNBOOK.md`
- comandi rapidi: `Makefile` (`make help`), inclusi `restart-fe`, `restart-be`, `restart` per aggiornare codice con lo stack già avviato (vedi [Setup Ambienti](#setup-ambienti-di-sviluppo-prima-di-make))

## Setup Da Zero: Deploy Automatico GitHub

Questa sezione descrive i passi minimi per attivare deploy automatico da GitHub verso:
- server produzione (DigitalOcean)
- server mirror (Raspberry Pi)

### 1) Prerequisiti generali

- Repository GitHub con workflow attivi in `.github/workflows/`.
- Branch `main` già protetto come branch di release.
- Sul server remoto: `git`, `docker` + `docker compose v2`, `curl`.
- DNS/host già risolti (`A` record o DDNS) e endpoint health raggiungibile.

### 2) Generare chiave SSH dedicata CI

Esegui sul tuo PC (non sul server), una chiave per ogni target o una chiave comune:

```bash
ssh-keygen -t ed25519 -C "github-actions-kor35" -f ~/.ssh/kor35_actions
```

Otterrai:
- privata: `~/.ssh/kor35_actions`
- pubblica: `~/.ssh/kor35_actions.pub`

### 3) Installare la chiave pubblica sui server

Su ogni server (DO e Pi), aggiungi il contenuto di `.pub` in `~/.ssh/authorized_keys` dell’utente deploy:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
cat >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Incolla la chiave pubblica e salva.

### 4) Aggiungere i GitHub Secrets

Repository GitHub -> **Settings -> Secrets and variables -> Actions -> New repository secret**.

#### Produzione (obbligatori)

- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_SSH_KEY` (contenuto della chiave privata `kor35_actions`)
- `SERVER_SSH_PORT` (opzionale, default `22`)

#### Produzione (opzionali consigliati)

- `PRODUCTION_HEALTHCHECK_URL` (es. `https://www.kor35.it/api/healthz/`)
- `SERVER_PROJECT_PATH` (es. `/srv/kor35`)
- `PROD_COMPOSE_PROJECT_NAME` (es. `kor35-prod`)

#### Mirror Raspberry (obbligatori)

- `MIRROR_SERVER_HOST`
- `MIRROR_SERVER_USER`
- `MIRROR_SERVER_SSH_KEY` (può essere la stessa privata o una dedicata)
- `MIRROR_SERVER_SSH_PORT` (opzionale)

#### Mirror Raspberry (opzionali consigliati)

- `MIRROR_ROOT_PATH` (default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_PATH`
- `MIRROR_BACKEND_REPO_URL` (bootstrap da zero, opzionale)
- `MIRROR_COMPOSE_PROJECT_NAME` (es. `kor35-replica`)
- `MIRROR_HEALTHCHECK_URL`

### 4.1) Tabella rapida Secrets GitHub Actions

| Secret | Scope | Obbligatorio | Esempio | Note |
|---|---|---|---|---|
| `SERVER_HOST` | Produzione | Sì | `203.0.113.10` | Host/IP server DO |
| `SERVER_USER` | Produzione | Sì | `deploy` | Utente SSH deploy |
| `SERVER_SSH_KEY` | Produzione | Sì | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Chiave privata CI |
| `SERVER_SSH_PORT` | Produzione | No | `22` | Se diverso dalla porta standard |
| `PRODUCTION_HEALTHCHECK_URL` | Produzione | No (consigliato) | `https://www.kor35.it/api/healthz/` | Se impostato, fallisce il workflow se non raggiungibile |
| `SERVER_PROJECT_PATH` | Produzione | No (consigliato) | `/srv/kor35` | Path repo monorepo sul server |
| `PROD_COMPOSE_PROJECT_NAME` | Produzione | No | `kor35-prod` | Nome progetto compose per evitare collisioni |
| `MIRROR_SERVER_HOST` | Mirror | Sì | `kor35.ddns.net` | Host/IP Raspberry |
| `MIRROR_SERVER_USER` | Mirror | Sì | `pi` | Utente SSH mirror |
| `MIRROR_SERVER_SSH_KEY` | Mirror | Sì | `-----BEGIN OPENSSH PRIVATE KEY-----...` | Chiave privata CI |
| `MIRROR_SERVER_SSH_PORT` | Mirror | No | **`10022`** | NAT router → Pi:22 |
| `MIRROR_ROOT_PATH` | Mirror | No | `/home/pi/kor35-replica` | Root progetto mirror |
| `MIRROR_BACKEND_PATH` | Mirror | No | `/home/pi/kor35-replica` | Fallback path repo se `MIRROR_ROOT_PATH` non esiste |
| `MIRROR_HEALTHCHECK_URL` | Mirror | No (forte consigliato) | `https://kor35.ddns.net/api/healthz/` | Validazione fine deploy |
| `MIRROR_BACKEND_REPO_URL` | Mirror | Solo se bootstrap da zero | `https://github.com/allanon74/kor35.git` | Clonato se la repo non esiste sul Pi |
| `MIRROR_COMPOSE_PROJECT_NAME` | Mirror | No | `kor35-replica` | Previene collisioni nomi container |

Note pratiche:
- Dove possibile imposta sempre i path espliciti (`SERVER_PROJECT_PATH`, `MIRROR_*_PATH`).
- Usa chiavi SSH dedicate alla CI e ruotale periodicamente.
- Se un secret è “No” ma lo usi in pipeline, trattalo come obbligatorio nel tuo contesto.

### 5) Preparazione server Produzione (Docker monorepo)

Esempio minimo:

```bash
sudo mkdir -p /srv/kor35
sudo chown -R <deploy-user>:<deploy-user> /srv/kor35
cd /srv/kor35
git clone https://github.com/allanon74/kor35.git .
cp config/env_templates/backend.prod.env.example backend/.env.prod
nano backend/.env.prod
# Django legge anche backend/.env (vedi kor35/settings.py): punta al profilo con un symlink
cd backend && ln -sf .env.prod .env && cd ..
cd config/docker
KOR35_BACKEND_ENV_FILE=/srv/kor35/backend/.env.prod \
docker compose -f compose.base.yml -f compose.prod.yml up -d --build
```

**Nota su `backend/.env`:** `settings.py` chiama `read_env(BASE_DIR / '.env')`. Il compose usa `KOR35_BACKEND_ENV_FILE` (es. `.env.prod`) e va bene per i container; per allineare anche comandi `manage.py` eseguiti a mano nella cartella `backend`, crea un symlink al file del profilo, ad esempio:

```bash
cd /srv/kor35/backend
ln -sf .env.prod .env
```

Stesso schema per il mirror: `ln -sf .env.mirror .env`. In alternativa puoi usare `cp` invece del symlink, ma dovrai ricordarti di aggiornare due file quando cambi la configurazione.

Verifica endpoint health lato produzione:

```bash
curl -fsS https://www.kor35.it/api/healthz/
```

### 6) Preparazione server Mirror (Docker)

Esempio minimo:

```bash
mkdir -p /home/pi/kor35-replica
cd /home/pi/kor35-replica
git clone https://github.com/allanon74/kor35.git .
cd config/docker
docker compose -f compose.base.yml -f compose.mirror.yml up -d --build
```

Verifica:

```bash
docker compose -f compose.base.yml -f compose.mirror.yml ps
curl -fsS https://kor35.ddns.net/api/healthz/
```

### 7) Primo test workflow

1. Push su `main` con modifica banale.
2. Controlla GitHub Actions:
   - `production-deploy` OK
   - `mirror-deploy` OK
3. Verifica servizi su DO/Pi con healthcheck.

### 7.1) Pre-flight checklist (prima del deploy)

Esegui questa checklist prima di lanciare `workflow_dispatch` o prima di fare push su `main`:

1. **Secrets presenti su GitHub**
   - Verifica almeno gli obbligatori (`SERVER_*`, `MIRROR_*` minimi) in:
     `Settings -> Secrets and variables -> Actions`.
2. **Path repo corretti sui server**
   - Production: `SERVER_PROJECT_PATH` punta alla root monorepo (es. `/srv/kor35`).
   - Mirror: `MIRROR_ROOT_PATH` (o fallback `MIRROR_BACKEND_PATH`) punta alla root monorepo.
3. **File env backend presenti sui server**
   - Production: `backend/.env.prod` (opzionale ma consigliato: `ln -sf .env.prod .env` in `backend/`)
   - Mirror: `backend/.env.mirror` (stesso schema: `ln -sf .env.mirror .env`)
4. **Docker compose monorepo presente sui server**
   - Deve esistere `config/docker/compose.base.yml` nella root repo.
5. **Healthcheck URL raggiungibili (se configurati)**
   - Production: `PRODUCTION_HEALTHCHECK_URL`
   - Mirror: `MIRROR_HEALTHCHECK_URL`

Comandi rapidi consigliati (da eseguire sui server):

```bash
# nella root repo
test -f config/docker/compose.base.yml && echo "compose ok"
test -f backend/.env.prod && echo "env prod ok"     # production
test -f backend/.env.mirror && echo "env mirror ok" # mirror

cd config/docker
docker compose -f compose.base.yml -f compose.prod.yml ps      # production
docker compose -f compose.base.yml -f compose.mirror.yml ps    # mirror
```

### 8) Safety (già attiva in questo branch)

- Deploy remoto consentito solo con `ref=main`.
- Branch diversi da `main` non devono propagarsi su DO/Pi.

---

## Setup Ambienti Di Sviluppo (prima di `make`)

### 1) Prerequisiti locali

- Docker + Docker Compose v2 funzionanti
- `make` installato
- repository `kor35` aggiornato su branch corretto

### 2) Crea env profilo

```bash
cd /home/django/progetti/kor35
./scripts/use_env_backend.sh --env dev-home
```

Compila `backend/.env.dev-home` (segreti reali), poi allinea `backend/.env` al profilo attivo.

Lo script `use_env_backend.sh` copia già il contenuto del profilo in `backend/.env`. In alternativa puoi usare un **symlink** (un solo file da modificare, come in produzione):

```bash
cd /home/django/progetti/kor35/backend
ln -sf .env.dev-home .env
```

Per un altro profilo, ad esempio `dev-office` o `prod` locale:

```bash
ln -sf .env.dev-office .env
# oppure
ln -sf .env.prod .env
```

### 3) Setup e avvio stack

```bash
make setup
make up ENV=dev-home
# se hai vecchi container "kor35_wsl_*" che occupano porte:
make up ENV=dev-home CLEANUP_LEGACY=1
```

**Dopo ogni spegnimento del PC** (WSL + Docker Desktop riavviati), usa sempre il recreate del nginx:

```bash
make up ENV=dev-home RECREATE_FRONTEND=1
```

Senza `RECREATE_FRONTEND=1`, `http://127.0.0.1:8080/` puo' dare connection reset / `ERR_EMPTY_RESPONSE` anche con tutti i container `Up`. Vedi `docs/WSL_DEV_SETUP.md`.

### 4) Aggiornare il codice con lo stack già avviato

Con `dev-home` (e profili analoghi) il backend è montato da disco nel container: **non serve** `make down` / `make up` solo per ricaricare i `.py`.

| Comando | Cosa fa |
|--------|---------|
| `make restart-fe ENV=dev-home` | Esegue `npm run build`, copia la build in `react_build`, poi **`docker compose restart frontend`** (Nginx che serve gli statici). Usa lo stesso `ENV` dello stack. Se la UI resta vecchia, prova refresh forzato o svuota cache / service worker PWA. |
| `make restart-be ENV=dev-home` | Riavvia `backend` e `daphne` così Gunicorn/Daphne caricano i file Python aggiornati. Flag opzionali: `RUN_PIP_INSTALL=1` (esegue `pip install -r requirements.txt`), `RUN_MIGRATIONS=1` (esegue `migrate --noinput`), `RUN_COLLECTSTATIC=1` (esegue `collectstatic --noinput`). |
| `make restart ENV=dev-home` | Esegue in sequenza **`restart-fe`** e poi **`restart-be`**. Supporta gli stessi flag opzionali di `restart-be` (`RUN_PIP_INSTALL`, `RUN_MIGRATIONS`, `RUN_COLLECTSTATIC`). |

Esempio completo (frontend + backend + step opzionali backend):

```bash
make restart ENV=dev-home RUN_PIP_INSTALL=1 RUN_MIGRATIONS=1 RUN_COLLECTSTATIC=1
```

Per solo backend, in alternativa: `docker restart kor35_devhome_backend kor35_devhome_daphne` (nomi tipici con profilo `dev-home`).

### 5) Verifica operatività

```bash
make status ENV=dev-home
make logs ENV=dev-home
```

Frontend:
- `http://127.0.0.1:8080` (`dev-home`)
- `http://127.0.0.1:8081` (`dev-office`)

### 6) Sync opzionale da master/pi

```bash
make sync-db ENV=dev-home
make sync-db-full ENV=dev-home
# diagnostica conflitti catalogo SegnoZodiacale (numero/sync_id)
make sync-db-diagnose ENV=dev-home
make sync-db-full-diagnose ENV=dev-home
make sync-media
make sync-media-push
# solo mirror: full DB diagnose + media push + media pull
make mirror-resync-after-event ENV=mirror
```

### Troubleshooting `sync-db`

- `service "backend" is not running`: verifica stack attivo con `make status ENV=<profilo>`; su mirror usa i target `make` aggiornati (impostano `COMPOSE_PROJECT_NAME` corretto).
- `duplicate key value ... sync_id`: esegui diagnostica con `make sync-db-diagnose ENV=<profilo>` (o `sync-db-full-diagnose`) e risolvi i duplicati `SegnoZodiacale` seguendo l'output.
- Sync completa ma con warning `catalog.segnozodiacale: salto ...`: è un conflitto storico non bloccante; pianifica bonifica dati e rilancia `sync-db-full-diagnose`.
- Errori di rete/HTTP verso master: controlla `EDGE_SYNC_URL`, token e raggiungibilità (`curl` verso endpoint `/api/sync/edge/` dal nodo locale).

### Mirror Pi: SSH e rete (Cursor / PC dev)

- **SSH pubblico:** `kor35.ddns.net:10022`, utente `pi`, alias consigliato `kor35-mirror`
- **Template:** `config/mirror/ssh-config.example` → `~/.ssh/config`
- **Regola agenti Cursor:** `.cursor/rules/mirror-pi-ops.mdc`
- **Runbook rete:** `docs/MIRROR_PI_NETWORK.md` (modalità `router` / `event`, Omada, `Pi_Emergenza`)

```bash
# Dal PC dev (chiave ~/.ssh/id_docker in authorized_keys sul Pi)
make mirror-pi-check
make mirror-pi-configure MIRROR_NETWORK_MODE=router MIRROR_NETWORK_AUTO_BOOT=0
ssh kor35-mirror 'cd /home/pi/kor35-replica && ./scripts/mirror_network_check.sh'
```

Script rete: `scripts/mirror_pi_remote.sh`, `scripts/mirror_configure_network.sh`, `install_mirror_network.sh`, `mirror_network_apply_mode.sh`.

### Mirror Pi: automazione sync (DB + media)

Script principali:

- `scripts/sync_media_pull_wsl_pi_like.sh`: pull-only media da master verso nodo locale.
- `scripts/sync_media_push_wsl_pi_like.sh`: push-only media dal nodo locale verso master (senza delete remoto).
- `scripts/mirror_resync_after_event.sh`: sequenza post-evento (`sync-db-full-diagnose` + `sync-media-push` + `sync-media`).
- `scripts/install_mirror_sync_services.sh`: installa/configura/abilita i servizi systemd mirror.

Unit systemd versionate nel repo:

- `config/systemd/kor35-mirror-db-sync.service`
- `config/systemd/kor35-mirror-db-sync.timer`
- `config/systemd/kor35-mirror-resync.service`
- `config/systemd/kor35-mirror-media-sync.service`
- `config/systemd/kor35-mirror-media-sync.timer`
- `config/systemd/kor35-mirror-db-backup.service`
- `config/systemd/kor35-mirror-db-backup.timer`

Prerequisiti su Pi:

- repo in `/home/pi/kor35-replica` (o path custom passato allo script)
- file `.env.sync-media` configurato nella root repo
- accesso SSH al master funzionante (chiave privata + host key)

Installazione servizi mirror con script unico:

```bash
cd /home/pi/kor35-replica
sudo ./scripts/install_mirror_sync_services.sh \
  --repo-path /home/pi/kor35-replica \
  --user pi \
  --group pi \
  --db-interval 2m \
  --media-calendar "*-*-* 22:30:00" \
  --backup-calendar "*-*-* 05:00:00" \
  --backup-retention-days 15 \
  --backup-dir /home/pi/backups/kor35/db
```

Lo script:

- copia le unit in `/etc/systemd/system`
- sostituisce path repo / user / group
- imposta intervallo timer DB e calendario timer media
- imposta backup DB giornaliero (default 05:00), retention (default 15 giorni) e directory backup
- esegue `systemctl daemon-reload`
- abilita/avvia i timer `kor35-mirror-db-sync.timer`, `kor35-mirror-media-sync.timer`, `kor35-mirror-db-backup.timer`

Verifica:

```bash
systemctl list-timers | grep -E 'kor35-mirror-(db-sync|media-sync)'
systemctl status kor35-mirror-db-sync.timer --no-pager
systemctl status kor35-mirror-media-sync.timer --no-pager
systemctl status kor35-mirror-db-backup.timer --no-pager
```

Modalità operative consigliate:

- **Modalità Evento (offline/instabile, sync aggressivo)**  
  DB ogni 1 minuto, media ogni notte:

  ```bash
  cd /home/pi/kor35-replica
  sudo ./scripts/install_mirror_sync_services.sh \
    --repo-path /home/pi/kor35-replica \
    --user pi \
    --group pi \
    --db-interval 1m \
    --media-calendar "*-*-* 22:30:00" \
    --backup-calendar "*-*-* 05:00:00" \
    --backup-retention-days 15 \
    --backup-dir /home/pi/backups/kor35/db
  ```

- **Modalità Normale (regime stabile, carico ridotto)**  
  DB ogni 5 minuti, media ogni notte:

  ```bash
  cd /home/pi/kor35-replica
  sudo ./scripts/install_mirror_sync_services.sh \
    --repo-path /home/pi/kor35-replica \
    --user pi \
    --group pi \
    --db-interval 5m \
    --media-calendar "*-*-* 22:30:00" \
    --backup-calendar "*-*-* 05:00:00" \
    --backup-retention-days 15 \
    --backup-dir /home/pi/backups/kor35/db
  ```

Esecuzioni manuali utili:

```bash
# sync DB one-shot (systemd)
sudo systemctl restart kor35-mirror-db-sync.service
sudo journalctl -u kor35-mirror-db-sync.service -n 120 --no-pager

# riallineamento completo post-evento
sudo systemctl start kor35-mirror-resync.service
sudo journalctl -u kor35-mirror-resync.service -n 200 --no-pager

# backup DB one-shot
sudo systemctl start kor35-mirror-db-backup.service
sudo journalctl -u kor35-mirror-db-backup.service -n 120 --no-pager
```

## Appendice: Comandi rapidi quotidiani

Bootstrap ambiente dev-home (prima volta):

```bash
cd /home/django/progetti/kor35
./scripts/use_env_backend.sh --env dev-home
cd backend && ln -sf .env.dev-home .env && cd ..
make setup
make up ENV=dev-home
```

Avvio mattina dopo reboot WSL/Docker:

```bash
make up ENV=dev-home RECREATE_FRONTEND=1
```

Dopo modifiche a React o Python (stack già su), vedi il punto **4) Aggiornare il codice con lo stack già avviato** nella sezione [Setup Ambienti](#setup-ambienti-di-sviluppo-prima-di-make) (`make restart-fe`, `make restart-be`, `make restart` + flag opzionali `RUN_PIP_INSTALL=1`, `RUN_MIGRATIONS=1`, `RUN_COLLECTSTATIC=1`).

Controllo stato:

```bash
make status ENV=dev-home
make logs ENV=dev-home
```

Cambio profilo:

```bash
./scripts/use_env_backend.sh --env dev-office
cd backend && ln -sf .env.dev-office .env && cd ..
make up ENV=dev-office
```

(`use_env_backend.sh` aggiorna già `backend/.env`; il `ln -sf` è opzionale se preferisci solo il symlink al file di profilo.)

Stop:

```bash
make down ENV=dev-home
```

Cleanup legacy (vecchio stack WSL):

```bash
make cleanup-legacy
```
