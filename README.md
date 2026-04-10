# kor35
sito kor35

## Indice

- [Panoramica rapida](#panoramica-rapida)
- [Struttura repository](#struttura-repository)
- [Deploy sicuro (GitHub Actions)](#deploy-sicuro-github-actions)
- [Sviluppo locale in WSL](#sviluppo-locale-in-wsl)
- [Setup Da Zero: Deploy Automatico GitHub](#setup-da-zero-deploy-automatico-github)
- [Setup Ambienti Di Sviluppo (prima di `make`)](#setup-ambienti-di-sviluppo-prima-di-make)
- [Appendice: Comandi rapidi quotidiani](#appendice-comandi-rapidi-quotidiani)

## Panoramica rapida

Monorepo KOR35 con architettura:
- `backend/` Django + DRF + Channels
- `frontend/` React/Vite
- `config/docker/` compose base + override ambiente
- `scripts/` automazione operativa (`up/down/logs/status/sync`)

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

## Deploy sicuro (GitHub Actions)

Workflow principale: `.github/workflows/deploy.yml`
Workflow secondari in `frontend/.github/workflows/` sono legacy/storici e non governano il deploy monorepo corrente.

- Trigger automatico su `push` in `main` + trigger manuale (`workflow_dispatch`) con:
  - `ref`: branch/tag/SHA da rilasciare
  - `run_migrations`: abilita/disabilita migrate
- Fasi:
  - `guard-main-ref`: blocca deploy se `ref != main`
  - `build-frontend`: se in questo deploy sono cambiati file sotto `frontend/`, su **GitHub Actions** esegue `npm ci` e `npm run build` e salva `dist/` come artifact (Node sul runner, **non sul server**)
  - `production-deploy`: opzionale `rsync` di `dist/` in `config/docker/nginx-docker/react_build/` sul server, poi SSH con `git pull` e `docker compose` (`compose.base + compose.prod`)
  - `mirror-deploy`: stesso `rsync` verso il Pi (se il frontend è stato buildato), poi SSH con compose mirror

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
- `MIRROR_SERVER_SSH_PORT` (default `22`)
- `MIRROR_ROOT_PATH` (default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_PATH` (fallback path monorepo, default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_REPO_URL` (usato solo bootstrap se il path non esiste)
- `MIRROR_COMPOSE_PROJECT_NAME` (default `kor35-replica`)
- `MIRROR_HEALTHCHECK_URL` (fortemente consigliato)

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

## Sviluppo locale in WSL

Per setup completo backend + frontend + Postgres locale + sync pull-only dal Master:

- vedi `docs/WSL_DEV_SETUP.md`
- stack Docker "Pi-like" WSL: `scripts/setup_wsl_pi_like.sh`, poi `scripts/up_wsl_pi_like.sh` / `scripts/down_wsl_pi_like.sh`
- media pull-only (rsync): `scripts/sync_media_pull_wsl_pi_like.sh`
- stato migrazione monorepo: `docs/MONOREPO_MIGRATION.md`
- env per ambiente: `config/env_templates/README.md`
- runbook docker ambienti: `docs/DOCKER_ENVIRONMENTS_RUNBOOK.md`
- comandi rapidi: `Makefile` (`make help`)

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
| `MIRROR_SERVER_SSH_PORT` | Mirror | No | `22` | Se custom |
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

### 4) Verifica operatività

```bash
make status ENV=dev-home
make logs ENV=dev-home
```

Frontend:
- `http://127.0.0.1:8080` (`dev-home`)
- `http://127.0.0.1:8081` (`dev-office`)

### 5) Sync opzionale da master/pi

```bash
make sync-db ENV=dev-home
make sync-media
```

## Appendice: Comandi rapidi quotidiani

Bootstrap ambiente dev-home:

```bash
cd /home/django/progetti/kor35
./scripts/use_env_backend.sh --env dev-home
cd backend && ln -sf .env.dev-home .env && cd ..
make setup
make up ENV=dev-home
```

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
