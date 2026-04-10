# Setup WSL sviluppo (backend + frontend + DB locale)

Questa guida prepara un ambiente locale completo in WSL con:
- backend Django (`/home/django/progetti/kor35/backend`)
- frontend Vite React (`/home/django/progetti/kor35/frontend`, fallback legacy `/home/django/progetti/kor35-app`)
- PostgreSQL + Redis locali via Docker
- sincronizzazione **pull-only** dal Master/Pi verso il DB locale

Include due modalita':
- **Fast dev**: backend `runserver` + frontend `vite dev`
- **Pi-like Docker**: stack all-in-docker con Nginx, Gunicorn, Daphne, Postgres, Redis

## 1) Prerequisiti

- WSL con `python3`, `pip`, `venv`, `node`, `npm`, `docker`, `docker compose`
- Accesso al server Master/Pi (URL endpoint sync + token edge)

## 2) Backend: variabili ambiente

Nel repo backend:

```bash
cd /home/django/progetti/kor35/backend
cp ../.env.wsl.example .env
```

Compila nel file `.env` almeno:
- `EDGE_SYNC_URL` (es. `https://<host-master>/api/sync/edge/`)
- `EDGE_SYNC_TOKEN` (lo stesso token accettato dal Master)

## 3) Avvio servizi locali DB/Redis

Nel repo backend:

```bash
cd /home/django/progetti/kor35
docker compose -f config/docker/compose.dev-standalone.yml up -d
```

Verifica:

```bash
docker compose -f config/docker/compose.dev-standalone.yml ps
```

## 4) Backend Django locale

Nel repo backend:

```bash
cd /home/django/progetti/kor35/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Backend disponibile su `http://127.0.0.1:8000`.

## 5) Frontend locale (Vite)

Nel repo frontend (monorepo):

```bash
cd /home/django/progetti/kor35/frontend
cp .env.example .env
npm install
npm run dev
```

Il frontend usa percorsi relativi `/api` e `/media`, con proxy Vite verso `127.0.0.1:8000` in sviluppo.

## 6) Prima sincronizzazione pull-only

Con backend avviato e `.env` configurato:

```bash
cd /home/django/progetti/kor35/backend
source .venv/bin/activate
python manage.py sync_edge_node --pull-only
```

Questo comando **non invia** modifiche locali al Master.

## 7) Allineamento continuo pull-only

Per mantenere il DB locale allineato in polling:

```bash
cd /home/django/progetti/kor35/backend
source .venv/bin/activate
SYNC_INTERVAL_SECONDS=60 ../scripts/sync_edge_pull_only.sh
```

Il loop richiama internamente:

```bash
python manage.py sync_edge_node --pull-only
```

## 8) Note operative importanti

- Mantieni `--pull-only` in locale se vuoi evitare qualsiasi push dati.
- Lo stato di sync viene salvato in `EDGE_SYNC_STATE_FILE` (default `.edge_sync_state.json`).
- Se vuoi forzare un pull completo, elimina il file stato o usa `--since` sul comando Django.
- Per fermare i container locali:

```bash
cd /home/django/progetti/kor35
docker compose -f config/docker/compose.dev-standalone.yml down
```

## 9) Modalita' Pi-like completa (Docker)

Se vuoi replicare il comportamento mirror/Pi in WSL:

```bash
cd /home/django/progetti/kor35
./scripts/setup_wsl_pi_like.sh
```

Poi avvia lo stack (consigliato):

```bash
cd /home/django/progetti/kor35
./scripts/up_wsl_pi_like.sh
```

In un solo comando (setup + build frontend + avvio):

```bash
./scripts/up_wsl_pi_like.sh --setup
```

Altri comodi:

```bash
./scripts/logs_wsl_pi_like.sh              # log tutti i servizi
./scripts/logs_wsl_pi_like.sh backend    # solo backend
./scripts/down_wsl_pi_like.sh             # stop
./scripts/down_wsl_pi_like.sh --volumes   # stop e cancella dati DB del compose
```

Opzioni `up`: `--no-build` (riavvio senza rebuild immagini), `--setup` (come `setup_wsl_pi_like.sh`), `--skip-collectstatic`.

`collectstatic` viene eseguito automaticamente da `up_wsl_pi_like.sh` (a meno di `--skip-collectstatic`).

Sync media pull-only (rsync):

```bash
cd /home/django/progetti/kor35
source .env
./scripts/sync_media_pull_wsl_pi_like.sh
```

Variabili usate per rsync:
- `WSL_PI_REMOTE_SSH_USER`
- `WSL_PI_REMOTE_SSH_HOST`
- `WSL_PI_REMOTE_SSH_PORT`
- `WSL_PI_REMOTE_MEDIA_DIR`

URL:
- `http://127.0.0.1:8080`

Equivalente manuale (stessa directory del compose):

```bash
cd /home/django/progetti/kor35/config/docker/nginx-docker
docker compose -f docker-compose.wsl-pi.yml up -d --build
```
