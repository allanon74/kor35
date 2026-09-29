# KOR35 — note per agenti (Cursor / CI)

Progetto Django + React, architettura **master** (prod) + **replica** (mirror/Pi, dev-office), sync DB edge LWW.

## Regole persistenti

| Fonte | Contenuto |
|-------|-----------|
| `.cursorrules` | Regole globali: UUID/sync, API, Docker, staff dashboard |
| `.cursor/rules/edge-sync.mdc` | Sync LWW, MTI, tombstone, checklist implementazione |
| `.cursor/rules/prod-docker-ops.mdc` | SSH prod (`kor35-prod` + proxy corkscrew), compose, log, sync |
| `.cursor/rules/mirror-pi-ops.mdc` | SSH mirror Pi: **`pi@kor35.ddns.net:10022`**, chiave `~/.ssh/id_docker`, `make mirror-pi-*` |
| `.cursor/rules/wiki-staff-ops.mdc` | Wiki staff da `docs/wiki/staff/` → `make wiki-staff-sync` |
| `.cursor/rules/android-capacitor.mdc` | Shell Android Capacitor (PWA-first, FCM nativo) |
| `docs/ANDROID_CAPACITOR.md` | Runbook build/sync app Android |
| `docs/wiki/carte/README.md` | Wiki regolamento carte → `make wiki-carte-sync` |
| `.cursor/rules/django-tests-docker.mdc` | Test Django in Docker: **sempre `--keepdb`** + `exec -T` |
| `.cursor/environment.json` + `.cursor/cloud/` | Cloud Agent DinD (Docker CE + `dev-home`); vedi sezione Cloud sotto |
| `config/docker/SYNC.md` | Runbook Docker: ruoli nodo, `make sync-db`, media rsync |
| `docs/card-platform/` | Roadmap Card Studio / Card Arena, allineamento DB, contratti JSON |

## Checklist rapida (feature che tocca il DB)

1. Modello sincronizzabile? → `sync_id` + `updated_at`, no auto-increment per PK sync.
2. Migrazione? → `make migrate` su ogni profilo che fa sync (prod, mirror, dev-office).
3. Logica sync? → `syncing.py` / `edge_sync.py` / `sync_edge_node.py` in parallelo se modifichi apply.
4. MTI (Tessitura, Infusione, …)? → non sovrascrivere figlio se `remote_updated_at < local.updated_at`.
5. Media? → solo path in JSON; file con `make sync-media` / rsync.
6. Comandi → Docker-first (`make … ENV=…`), vedi `Makefile` help.
7. Mirror Pi rete/SSH da PC dev → `make mirror-pi-configure`, `make mirror-pi-check` (`.cursor/rules/mirror-pi-ops.mdc`).
8. Wiki staff (make / mirror) → `docs/wiki/staff/` + `make wiki-staff-sync` (`.cursor/rules/wiki-staff-ops.mdc`).
9. Test backend → container + `exec -T` + **`--keepdb`** (vedi `.cursor/rules/django-tests-docker.mdc`); senza `--keepdb` Django chiede `yes/no` e il comando si blocca.

## Profili ambiente

- `dev-home` — locale isolato (sync opzionale)
- `dev-office` — replica verso prod (`:8081`)
- `mirror` — Pi / evento offline (`ssh -p 10022 pi@kor35.ddns.net` o `make mirror-pi-check`, vedi `.cursor/rules/mirror-pi-ops.mdc`)
- `prod` — master (`KOR35_SYNC_NODE_ROLE=master`)

Template env: `config/env_templates/backend.<profilo>.env.example`

## Shell Android (Capacitor)

- PWA resta il canale completo per iOS/Windows/browser.
- App Android = Capacitor WebView + FCM/chiamate native; UI identica alla PWA.
- Build consigliata: `make android-apk` (WSL, senza Android Studio; APK in `C:\dev\kor35-apk\`).
- Con Studio: `make android-sync WIN=1`, poi apri **solo** `C:\dev\kor35-app\android` (`make android-path`). Path **bloccato** — non usare `C:\dev\kor35-android` né il parent `C:\dev\kor35-app`.
- Regole: `.cursor/rules/android-capacitor.mdc`.

## Cursor Cloud specific instructions

Ambiente versionato in `.cursor/` (DinD):

| File | Ruolo |
|------|--------|
| `.cursor/Dockerfile` | Ubuntu 24.04 + Docker CE + fuse-overlayfs + iptables-legacy |
| `.cursor/environment.json` | `install` / `start` Cloud Agent |
| `.cursor/cloud/install.sh` | Bootstrap Build (idempotente); crea `backend/.env.dev-home` se manca |
| `.cursor/cloud/start.sh` | Avvia `dockerd` + SSH (`ID_DOCKER`) |
| `.cursor/cloud/README.md` | Dettaglio secrets e smoke-test |

**Secrets** (dashboard Environment, non in git): `ID_DOCKER` (chiave SSH), `SECRET_KEY` (Django, consigliato).

**Profilo Cloud:** `ENV=dev-home` (stack locale isolato). Path workspace tipico: `/workspace`.

Dopo che `start.sh` ha avviato Docker:

```bash
docker info
test -f backend/.env.dev-home || cp config/env_templates/backend.dev-home.env.example backend/.env.dev-home

cd config/docker
export KOR35_BACKEND_ENV_FILE="$(pwd)/../../backend/.env.dev-home"
# Stack minimo per test backend (più leggero del full compose):
docker compose -f compose.base.yml -f compose.dev-home.yml up -d --build db redis backend

docker compose -f compose.base.yml -f compose.dev-home.yml exec -T backend \
  python manage.py test personaggi.tests_qr_multi_flow personaggi.tests_qr_random_pool \
  personaggi.tests_qr_minigioco pilotaggio.tests.test_qr_sottosistema -v 2 --keepdb
```

Note DinD:

- `dockerd` va avviato a ogni boot agent (`start.sh`); non sopravvive allo snapshot Build.
- Se `docker` manca, l’agent non sta usando il Build da `.cursor/Dockerfile` — ricostruire l’Environment.
- SSH mirror/prod resta opzionale via `ID_DOCKER` (vedi `.cursor/rules/mirror-pi-ops.mdc` / `prod-docker-ops.mdc`).
- Non usare `python manage.py test` sull’host Cloud: sempre `docker compose … exec -T backend … --keepdb`.

