# KOR35 — note per agenti (Cursor / CI)

Progetto Django + React, architettura **master** (prod) + **replica** (mirror/Pi, dev-office), sync DB edge LWW.

## Regole persistenti

| Fonte | Contenuto |
|-------|-----------|
| `.cursorrules` | Regole globali: UUID/sync, API, Docker, staff dashboard |
| `.cursor/rules/edge-sync.mdc` | Sync LWW, MTI, tombstone, checklist implementazione |
| `.cursor/rules/prod-docker-ops.mdc` | SSH prod (`kor35-prod` + proxy corkscrew), compose, log, sync |
| `.cursor/rules/mirror-pi-ops.mdc` | SSH mirror Pi (`kor35-mirror`, `kor35.ddns.net:10022`), rete router/evento, diagnostica |
| `.cursor/rules/wiki-staff-ops.mdc` | Wiki staff da `docs/wiki/staff/` → `make wiki-staff-sync` |
| `.cursor/rules/django-tests-docker.mdc` | Test Django in Docker: **sempre `--keepdb`** + `exec -T` |
| `config/docker/SYNC.md` | Runbook Docker: ruoli nodo, `make sync-db`, media rsync |

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
- `mirror` — Pi / evento offline (`ssh kor35-mirror`, vedi `.cursor/rules/mirror-pi-ops.mdc`)
- `prod` — master (`KOR35_SYNC_NODE_ROLE=master`)

Template env: `config/env_templates/backend.<profilo>.env.example`
