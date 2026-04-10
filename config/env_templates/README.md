# Template environment backend

Questa cartella contiene solo template versionati (`*.env.example`).

- `backend.dev-home.env.example`
- `backend.dev-office.env.example`
- `backend.mirror.env.example`
- `backend.prod.env.example`

I file reali con segreti non devono essere committati:

- `backend/.env`
- `backend/.env.dev-home`
- `backend/.env.dev-office`
- `backend/.env.mirror`
- `backend/.env.prod`

Uso rapido:

```bash
./scripts/use_env_backend.sh --env dev-home
./scripts/use_env_backend.sh --env prod
```
Template environment files per backend Django.

File disponibili:
- `backend.dev-home.env.example`
- `backend.dev-office.env.example`
- `backend.mirror.env.example`
- `backend.prod.env.example`

Uso consigliato:

1) Crea file ambiente reale dal template:

```bash
cp config/env_templates/backend.dev-home.env.example backend/.env.dev-home
cp config/env_templates/backend.prod.env.example backend/.env.prod
```

2) Oppure usa lo script helper:

```bash
./scripts/use_env_backend.sh --env dev-home
./scripts/use_env_backend.sh --env prod
```

Lo script crea (se mancante) `backend/.env.<profilo>` e aggiorna `backend/.env`
con lo stesso contenuto per compatibilità locale.

3) Avvio stack per ambiente:

```bash
./scripts/up_wsl_pi_like.sh --env dev-home --setup
./scripts/up_wsl_pi_like.sh --env dev-office
./scripts/up_wsl_pi_like.sh --env mirror
./scripts/up_wsl_pi_like.sh --env prod
```
