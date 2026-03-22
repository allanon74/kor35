# kor35
sito kor35

## Deploy sicuro (GitHub Actions)

Workflow principale: `.github/workflows/deploy.yml`

- Trigger automatico su `push` in `main` + trigger manuale (`workflow_dispatch`) con:
  - `ref`: branch/tag/SHA da rilasciare
  - `run_migrations`: abilita/disabilita migrate
- Fasi:
  - `staging-validate`: deploy su staging, `migrate --plan`, `migrate --noinput`, `check --deploy`, `collectstatic`, healthcheck
  - `production-deploy`: deploy produzione con gli stessi controlli + healthcheck
  - `mirror-deploy`: deploy su Raspberry mirror (backend + frontend + build React + comando Docker)

Rollback manuale: `.github/workflows/rollback.yml`

- Trigger manuale con `rollback_ref` (SHA/tag/branch)
- Ripristina codice, installa dipendenze, `collectstatic`, restart servizi, healthcheck

### Secrets richiesti

Staging:
- `STAGING_SERVER_HOST`
- `STAGING_SERVER_USER`
- `STAGING_SERVER_SSH_KEY`
- `STAGING_SERVER_SSH_PORT` (opzionale, default 22)
- `STAGING_HEALTHCHECK_URL`

Produzione:
- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_SSH_PORT` (opzionale, default 22)
- `PRODUCTION_HEALTHCHECK_URL`

Mirror Raspberry:
- `MIRROR_SERVER_HOST`
- `MIRROR_SERVER_USER`
- `MIRROR_SERVER_SSH_KEY`
- `MIRROR_SERVER_SSH_PORT` (opzionale, default 22)
- `MIRROR_ROOT_PATH` (opzionale, default `/home/pi/kor35-replica`)
- `MIRROR_BACKEND_PATH` (opzionale, default `/home/pi/kor35-replica/backend_src`)
- `MIRROR_FRONTEND_PATH` (opzionale, default `/home/pi/kor35-replica/forntend_src`)
- `MIRROR_REACT_BUILD_PATH` (opzionale, default `/home/pi/kor35-replica/react_build`)
- `MIRROR_DEPLOY_COMMAND` (opzionale, default `docker compose up -d --build`)
- `MIRROR_HEALTHCHECK_URL` (opzionale, es. `https://kor35.ddns.net/api/healthz/`)

### Mirror / Docker: 502 Bad Gateway (dopo deploy o aggiornamenti)

Il 502 di Nginx di solito significa che **Gunicorn o Daphne non rispondono** (ancora in avvio, crash, DB/Redis non pronti, timeout).

Nel repo sono previsti:

- **`GET /api/healthz/`** — risposta `ok` senza query al DB (healthcheck Docker e monitoraggio).
- **Docker Compose** (`conf/nginx-docker/docker-compose.yml`): `healthcheck` su `db`, `redis`, `backend`, `daphne`; Nginx (`frontend`) parte solo quando backend e daphne sono **healthy**; Gunicorn con `--timeout 120`.
- **Nginx**: timeout proxy più alti verso il backend e WebSocket.

**Sul Pi, dopo un aggiornamento:**

1. Attendi fino a ~2 minuti al primo avvio (import Django lento su ARM).
2. `docker compose ps` — verifica che `backend` e `daphne` siano `healthy`, non solo `Up`.
3. `docker compose logs backend --tail 80` — errori migrazioni, `ALLOWED_HOSTS`, DB, Redis.
4. Migrazioni pendenti: `docker compose exec backend python manage.py migrate --noinput`.
5. Test rapido: `curl -sk https://localhost/api/healthz/` (dal Pi) o dall’esterno con il tuo host.

**Workflow deploy:** imposta `MIRROR_HEALTHCHECK_URL` sull’URL pubblico di `/api/healthz/` così la pipeline fallisce se il mirror non è davvero servibile.

### Nota importante

Se non hai un server staging separato puoi riusare i secrets di produzione anche per `STAGING_*`.
