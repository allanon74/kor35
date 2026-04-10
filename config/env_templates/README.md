# Template environment backend

Cartella versionata: `config/env_templates/*.env.example` (template senza segreti).

File:

- `backend.dev-home.env.example`
- `backend.dev-office.env.example`
- `backend.mirror.env.example`
- `backend.prod.env.example`

I file reali con segreti **non** vanno committati:

- `backend/.env`
- `backend/.env.dev-home`
- `backend/.env.dev-office`
- `backend/.env.mirror`
- `backend/.env.prod`

## Variabili effettive

Chiavi principali lette da `kor35/settings.py`:

- `SECRET_KEY`, `ALLOWED_HOSTS` (lista separata da virgole, senza spazi)
- `DEBUG`, `DB_*`, `REDIS_HOST` (quest’ultimo spesso da compose), edge sync, OAuth, SMTP
- `EXTRA_CSRF_TRUSTED_ORIGINS`, `EXTRA_CORS_ALLOWED_ORIGINS` (si aggiungono alle liste base in `settings.py`)

Con `ENVIRONMENT=raspberry_docker` (come in `compose.base.yml`) Django aggiunge `*` a `ALLOWED_HOSTS` e abilita `CORS_ALLOW_ALL_ORIGINS` per mirror/dev Docker.

`docker compose` sovrascrive nel container: `DB_HOST`, `DB_PORT`, `REDIS_HOST`, `ENVIRONMENT`, `EDGE_SYNC_STATE_FILE`.

## Uso rapido

```bash
cp config/env_templates/backend.dev-home.env.example backend/.env.dev-home
cp config/env_templates/backend.prod.env.example backend/.env.prod
```

Oppure:

```bash
./scripts/use_env_backend.sh --env dev-home
./scripts/use_env_backend.sh --env prod
```

Poi compila password e segreti. Avvio stack:

```bash
./scripts/up_wsl_pi_like.sh --env dev-home --setup
./scripts/up_wsl_pi_like.sh --env dev-office
./scripts/up_wsl_pi_like.sh --env mirror
./scripts/up_wsl_pi_like.sh --env prod
```

Lo script `use_env_backend.sh` crea `backend/.env.<profilo>` se manca e copia il contenuto in `backend/.env` per compatibilità locale.
