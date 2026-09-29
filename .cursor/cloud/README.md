# Cloud Agent KOR35 — Docker-in-Docker

Configurazione versionata per Cursor Cloud Agents.

| File | Ruolo |
|------|--------|
| `../Dockerfile` | Immagine Ubuntu 24.04 + Docker CE + fuse-overlayfs |
| `../environment.json` | `install` / `start` + porta 8080 |
| `install.sh` | Bootstrap Build (idempotente; crea `.env.dev-home` se manca) |
| `start.sh` | Per-boot: avvia `dockerd` + SSH da secret `ID_DOCKER` |
| `ssh_setup.sh` | Alias `kor35-mirror` / `kor35-prod` |

## Secrets (dashboard Environment)

| Nome | Obbligatorio | Uso |
|------|--------------|-----|
| `ID_DOCKER` | per SSH remoto | Chiave privata OpenSSH (stessa di WSL) |
| `SECRET_KEY` | consigliato | Django `backend/.env.dev-home` |

## Dopo il primo Build

```bash
docker info
cd config/docker
export KOR35_BACKEND_ENV_FILE="$(pwd)/../../backend/.env.dev-home"
docker compose -f compose.base.yml -f compose.dev-home.yml up -d --build db redis backend
# test QR:
docker compose -f compose.base.yml -f compose.dev-home.yml exec -T backend \
  python manage.py test personaggi.tests_qr_multi_flow -v 2 --keepdb
```

Vedi anche `AGENTS.md` → sezione **Cursor Cloud specific instructions**.
