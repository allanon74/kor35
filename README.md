# kor35
sito kor35

## Deploy sicuro (GitHub Actions)

Workflow principale: `.github/workflows/deploy.yml`

- Trigger manuale (`workflow_dispatch`) con:
  - `ref`: branch/tag/SHA da rilasciare
  - `run_migrations`: abilita/disabilita migrate
- Fasi:
  - `staging-validate`: deploy su staging, `migrate --plan`, `migrate --noinput`, `check --deploy`, `collectstatic`, healthcheck
  - `production-approval`: gate manuale tramite environment `production`
  - `production-deploy`: deploy produzione con gli stessi controlli + healthcheck

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

### Nota importante

Per far funzionare l'approvazione manuale, configura nell'environment `production` i required reviewers in GitHub Settings.
