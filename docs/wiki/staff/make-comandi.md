# Comandi Make KOR35

Helper nella **root del monorepo**. Profili: `dev-home`, `dev-office`, `mirror`, `prod`.

```bash
make help
make <target> ENV=dev-home
```

Documentazione estesa: `docs/DOCKER_ENVIRONMENTS_RUNBOOK.md`, `config/docker/SYNC.md`.

---

## Setup e stack Docker

| Comando | Descrizione |
|---------|-------------|
| `make env ENV=<profilo>` | Crea/attiva `backend/.env.<profilo>` |
| `make setup` | Runtime + build frontend (dev) |
| `make up ENV=<profilo>` | Avvia stack (build + collectstatic) |
| `make up-no-build ENV=<profilo>` | Avvio senza rebuild immagini |
| `make up-no-static ENV=<profilo>` | Avvio senza collectstatic |
| `make down ENV=<profilo>` | Stop stack |
| `make down-volumes ENV=<profilo>` | Stop + rimozione volumi |
| `make status ENV=<profilo>` | Stato container |
| `make logs ENV=<profilo>` | Log live |
| `make cleanup-legacy` | Rimuove container legacy `kor35_wsl_*` |

**Opzioni utili**

- `RECREATE_FRONTEND=1` — dopo reboot WSL/Docker (dev-home)
- `ALLOW_DB_REINIT=1` — consente re-init DB se volume mancante
- `CLEANUP_LEGACY=1` — pulizia container legacy prima di `up`

---

## Migrazioni e statici

| Comando | Descrizione |
|---------|-------------|
| `make migrate ENV=<profilo>` | `migrate` nel container backend |
| `make makemigrations ENV=<profilo>` | Crea migrazioni (`MAKEMIGRATIONS_APP=personaggi` opzionale) |
| `make collectstatic ENV=<profilo>` | Collectstatic nel backend |

---

## Restart e deploy codice

| Comando | Descrizione |
|---------|-------------|
| `make restart-fe ENV=<profilo>` | Build React + restart nginx (skip npm su prod/mirror) |
| `make restart-fe-pilot ENV=<profilo>` | Build console pilota + reload nginx |
| `make restart-be ENV=<profilo>` | Restart backend + daphne |
| `make restart ENV=<profilo>` | `restart-fe` + `restart-be` |
| `make deploy-be ENV=<profilo>` | Rebuild backend/daphne + migrate + collectstatic |

**Opzioni su `restart-be` / `restart`**

- `RUN_MIGRATIONS=1`
- `RUN_PIP_INSTALL=1`
- `RUN_COLLECTSTATIC=1`

---

## Sync database e media (edge)

Master = `ENV=prod`. Replica = `dev-office`, `mirror`.

| Comando | Descrizione |
|---------|-------------|
| `make sync-db ENV=<profilo>` | Pull-only DB (`SYNC_SINCE=ISO` opzionale) |
| `make sync-db-full ENV=<profilo>` | Pull completo da 1970 |
| `make sync-db-diagnose ENV=<profilo>` | Pull + diagnostica SegnoZodiacale |
| `make sync-db-full-diagnose ENV=<profilo>` | Full pull + diagnostica |
| `make sync-media` | Pull media via rsync (`.env.sync-media`) |
| `make sync-media-push` | Push media verso master |
| `make mirror-resync-after-event ENV=mirror` | Post-evento: full DB diagnose + media push + pull |

---

## Pilotaggio

| Comando | Descrizione |
|---------|-------------|
| `make pilot-tick ENV=<profilo>` | Tick motore (one-shot) |
| `make pilot-tick-restart ENV=<profilo>` | Restart servizio `pilot_tick` |
| `make pilot-tick-loop ENV=<profilo>` | Worker foreground (debug) |
| `make pilot-tick-stop ENV=<profilo>` | Disabilita tick runtime |
| `make seed-componenti-nave ENV=<profilo>` | Placeholder catalogo 10 componenti nave (once per nodo; vedi `componenti-nave-riparazione`) |

Opzioni `seed-componenti-nave`:

- `COMPONENTI_NAVE_SKIP_IF_COMPLETE=1` (default) — nessuna azione se i 10 mattoni esistono
- `COMPONENTI_NAVE_SKIP_IF_COMPLETE=0` — integra record mancanti
- `COMPONENTI_NAVE_FORCE_COPPIE=1` — ricrea coppie opposte

---

## Mirror Pi — rete (sul Pi)

| Comando | Descrizione |
|---------|-------------|
| `make mirror-network-check ENV=mirror` | Diagnostica rete + stack |
| `sudo make mirror-configure ENV=mirror MIRROR_NETWORK_MODE=router` | Install + modalità |
| `sudo make mirror-install-network MIRROR_NETWORK_AUTO_BOOT=0` | Solo install unit |
| `sudo make mirror-network-mode MIRROR_NETWORK_MODE=event` | Switch router/event/auto |

`MIRROR_NETWORK_MODE`: `router` | `event` | `auto`  
`MIRROR_NETWORK_AUTO_BOOT=0` — preserva hotspot NetworkManager `Hotspot-Emergenza`.

---

## Mirror Pi — da PC dev (SSH)

SSH: `kor35-mirror` → `kor35.ddns.net:10022`, utente `pi`.

| Comando | Descrizione |
|---------|-------------|
| `make mirror-pi-check` | Diagnostica remota |
| `make mirror-pi-pull` | `git pull` sul Pi |
| `make mirror-pi-install-network MIRROR_NETWORK_AUTO_BOOT=0` | Install/aggiorna unit rete |
| `make mirror-pi-network-mode MIRROR_NETWORK_MODE=router` | Cambio modalità |
| `make mirror-pi-configure MIRROR_NETWORK_MODE=router` | Pull + install + mode + check |
| `make mirror-pi-update` | Pull + install (senza cambio mode) |

---

## Backup e Wiki staff

| Comando | Descrizione |
|---------|-------------|
| `make backup-db ENV=prod` | Dump DB + rotazione |
| `make wiki-staff-sync ENV=dev-home` | Aggiorna pagine Wiki staff da `docs/wiki/staff/` |
| Dashboard staff → Manuali PDF | Pannello «Wiki operatività tecnica» (stesso effetto, richiede Master+) |

---

## Produzione (riferimento)

SSH prod: alias `kor35-prod`, utente `deploy`, path `/srv/kor35`.

```bash
make status ENV=prod
make logs ENV=prod
make migrate ENV=prod
```

Vedi `.cursor/rules/prod-docker-ops.mdc`.
