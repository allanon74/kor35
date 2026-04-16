# Runbook Docker multi-ambiente

Questa guida descrive:
- struttura repository
- file `.env` per ambiente
- script operativi
- layout directory sui server (DO / Pi / locali)

## 1) Struttura repository

Struttura target in root:

- `backend/` codice Django
- `frontend/` codice React/Vite
- `config/` configurazioni runtime (docker/apache/env)
- `docs/` runbook e documentazione
- `scripts/` tooling operativo
- `extra/` quarantena file legacy/non classificati

Sottostrutture rilevanti:

- `config/docker/compose.base.yml`
- `config/docker/compose.dev-home.yml`
- `config/docker/compose.dev-office.yml`
- `config/docker/compose.mirror.yml`
- `config/docker/compose.prod.yml`
- `config/docker/compose.dev-standalone.yml` (db+redis stand-alone)
- `config/docker/nginx-docker/` (nginx conf + runtime dirs legacy)
- `config/env_templates/` template env backend per ambiente

## 2) Profili ambiente supportati

- `dev-home`
- `dev-office`
- `mirror`
- `prod`

Ogni profilo seleziona:
- override compose
- file env backend dedicato (`backend/.env.<profilo>`)

## 3) Gestione `.env` backend

Template disponibili:

- `config/env_templates/backend.dev-home.env.example`
- `config/env_templates/backend.dev-office.env.example`
- `config/env_templates/backend.mirror.env.example`
- `config/env_templates/backend.prod.env.example`

Script consigliato:

```bash
cd /home/django/progetti/kor35
./scripts/use_env_backend.sh --env dev-home
```

Effetto:
- crea (se manca) `backend/.env.dev-home` dal template
- copia lo stesso contenuto in `backend/.env`

Ripeti per gli altri profili:

```bash
./scripts/use_env_backend.sh --env dev-office
./scripts/use_env_backend.sh --env mirror
./scripts/use_env_backend.sh --env prod
```

### Campi `.env` da compilare sempre

Minimo necessario:
- `SECRET_KEY`
- `DB_*` (se non usi default compose)
- `EDGE_SYNC_URL`
- `EDGE_SYNC_TOKEN`
- `SMTP_*` se usi invio email
- `GOOGLE_OAUTH_*` se usi login Google

Note:
- i file `backend/.env*` sono ignorati da git
- non committare mai credenziali reali

## 4) Script operativi

### Setup iniziale locale

```bash
./scripts/setup_wsl_pi_like.sh
```

Fa:
- verifica backend/frontend
- prepara runtime dirs in `config/docker/nginx-docker/`
- build frontend e copia in `react_build`

### Backup DB (dump giornaliero + rotazione)

Script: `scripts/backup_db_daily.sh`

Caratteristiche:
- esegue `pg_dump` dal container `db` (quindi usa `POSTGRES_DB/POSTGRES_USER` del servizio)
- salva dump su file in formato **custom** (`.dump`) + checksum `.sha256`
- rotazione basata su `mtime`: elimina dump più vecchi di **14 giorni** (default)

Esecuzione manuale (esempio produzione):

```bash
cd /srv/kor35
make backup-db ENV=prod
```

Variabili opzionali:
- `KOR35_DB_BACKUP_DIR` (default: `/var/backups/kor35/db`)
- `KOR35_DB_BACKUP_RETENTION_DAYS` (default: `14`)

Esempio custom:

```bash
cd /srv/kor35
KOR35_DB_BACKUP_DIR=/var/backups/kor35/db \
KOR35_DB_BACKUP_RETENTION_DAYS=14 \
make backup-db ENV=prod
```

Schedulazione consigliata in produzione: **systemd timer**

File nel repo:
- `config/systemd/kor35-db-backup.service`
- `config/systemd/kor35-db-backup.timer`

Installazione (sul server):

```bash
sudo mkdir -p /var/backups/kor35/db
sudo chmod 700 /var/backups/kor35/db

sudo cp /srv/kor35/config/systemd/kor35-db-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kor35-db-backup.timer
```

Test e log:

```bash
sudo systemctl start kor35-db-backup.service
sudo journalctl -u kor35-db-backup.service -n 200 --no-pager
```

Alternativa (se preferisci): cron

```cron
30 3 * * * cd /srv/kor35 && KOR35_DB_BACKUP_DIR=/var/backups/kor35/db KOR35_DB_BACKUP_RETENTION_DAYS=14 make backup-db ENV=prod >> /var/log/kor35-db-backup.log 2>&1
```

### Avvio stack

```bash
./scripts/up_wsl_pi_like.sh --env dev-home --setup
```

Opzioni utili:
- `--env <profilo>`: `dev-home|dev-office|mirror|prod`
- `--setup`: esegue setup prima dell'up
- `--no-build`: evita rebuild immagini
- `--skip-collectstatic`: salta collectstatic

### Stato / log / stop

```bash
./scripts/status_wsl_pi_like.sh --env dev-home
./scripts/logs_wsl_pi_like.sh --env dev-home
./scripts/logs_wsl_pi_like.sh --env dev-home backend
./scripts/down_wsl_pi_like.sh --env dev-home
./scripts/down_wsl_pi_like.sh --env dev-home --volumes
```

### Sync DB pull-only

Locale (venv):

```bash
cd /home/django/progetti/kor35/backend
python manage.py sync_edge_node --pull-only
```

Pull completo (da epoch, per riallineare tutto il DB):

```bash
cd /home/django/progetti/kor35/backend
python manage.py sync_edge_node --pull-only --since "1970-01-01T00:00:00Z"
```

Loop continuo:

```bash
cd /home/django/progetti/kor35
SYNC_INTERVAL_SECONDS=60 ./scripts/sync_edge_pull_only.sh
```

### Sync media pull-only (rsync)

```bash
cd /home/django/progetti/kor35
# Variabili in shell oppure file `.env.sync-media` nella root repo
./scripts/sync_media_pull_wsl_pi_like.sh
```

Variabili usate:
- `WSL_PI_REMOTE_SSH_USER`
- `WSL_PI_REMOTE_SSH_HOST`
- `WSL_PI_REMOTE_SSH_PORT`
- `WSL_PI_REMOTE_SSH_IDENTITY` (opzionale)
- `WSL_PI_REMOTE_MEDIA_DIR`

## 5) Comandi docker manuali (senza script)

Esempio `dev-home`:

```bash
cd /home/django/progetti/kor35/config/docker
KOR35_BACKEND_ENV_FILE=/home/django/progetti/kor35/backend/.env.dev-home \
docker compose -f compose.base.yml -f compose.dev-home.yml up -d --build
```

Esempio `prod`:

```bash
cd /home/django/progetti/kor35/config/docker
KOR35_BACKEND_ENV_FILE=/home/django/progetti/kor35/backend/.env.prod \
docker compose -f compose.base.yml -f compose.prod.yml up -d --build
```

## 6) Layout directory server

### 6.1 DigitalOcean (production)

Path consigliato:

- `/srv/kor35/`
  - `backend/`
  - `frontend/` (sorgente opzionale, se build lato server)
  - `config/docker/`
  - `docs/`
  - `scripts/`
  - `.git/`

Runtime persistente (in `config/docker/nginx-docker/`):
- `postgres_data/`
- `media_data/`
- `static_data/`
- `react_build/`
- `certs/` (TLS produzione)
- `certs_ddns/` solo sul **mirror/Pi** (dominio DDNS), non sul server Docker di produzione

### 6.2 Raspberry mirror

Path consigliato:

- `/home/pi/kor35-replica/`
  - stessa struttura del repo
  - runtime in `config/docker/nginx-docker/`

Solo mirror:
- servizio `omada-controller` attivo tramite `compose.mirror.yml`

### 6.3 Local dev (home/office)

Path consigliato:

- `/home/<user>/progetti/kor35/`
  - usa script con `--env dev-home` o `--env dev-office`

## 7) Checklist primo avvio ambiente

1. `./scripts/use_env_backend.sh --env <profilo>`
2. compila `backend/.env.<profilo>`
3. `./scripts/up_wsl_pi_like.sh --env <profilo> --setup`
4. `./scripts/status_wsl_pi_like.sh --env <profilo>`
5. test:
   - `/api/healthz/`
   - admin login
   - frontend login
6. (opzionale) sync DB/media pull-only

## 8) Sicurezza e deploy

- deploy remoto consentito solo da branch `main` (workflow guard attiva)
- lavoro di migrazione su branch `docker`
- non usare branch non-main per deploy DO/Pi

## 9) Uso rapido con Makefile

In root repo è disponibile `Makefile` con target standard.

Mostra aiuto:

```bash
make help
```

Esempi tipici:

```bash
# 1) prepara env locale
make env ENV=dev-home

# 2) setup runtime + build frontend
make setup

# 3) avvia stack
make up ENV=dev-home

# opzionale: pulizia automatica vecchi container kor35_wsl_* prima dell'up
make up ENV=dev-home CLEANUP_LEGACY=1

# 3b) migrazioni
make makemigrations ENV=dev-home MAKEMIGRATIONS_APP=personaggi
make migrate ENV=dev-home

# 3c) collectstatic manuale
make collectstatic ENV=dev-home

# 4) controlla stato e log
make status ENV=dev-home
make logs ENV=dev-home

# 4b) restart rapido servizi (stack già avviato)
make restart-fe ENV=dev-home
make restart-be ENV=dev-home
make restart ENV=dev-home

# opzionali su restart-be/restart:
# - pip install requirements nel container backend
# - migrate
# - collectstatic
make restart ENV=dev-home RUN_PIP_INSTALL=1 RUN_MIGRATIONS=1 RUN_COLLECTSTATIC=1

# 5) sync DB pull-only
make sync-db ENV=dev-home

# 5b) sync DB pull-only completo (full refresh)
make sync-db-full ENV=dev-home

# 5c) sync DB pull-only da data custom (ISO datetime)
make sync-db ENV=dev-home SYNC_SINCE="2024-01-01T00:00:00Z"

# 6) stop stack
make down ENV=dev-home

# 7) cleanup manuale container legacy
make cleanup-legacy
```

Altri profili:

```bash
make up ENV=dev-office
make up ENV=mirror
make up ENV=prod
```
