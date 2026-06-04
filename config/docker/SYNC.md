# Sincronizzazione DB (Edge sync) e Docker

KOR35 replica dati tra **master** (produzione) e **replica** (dev-office, mirror/Pi) con Last-Write-Wins su `sync_id` + `updated_at`. I file media non passano nel JSON: solo `rsync` (`make sync-media`).

## Ruoli per profilo Compose

| Profilo Compose | `KOR35_SYNC_NODE_ROLE` | `EDGE_SYNC_URL` in `.env.*` | Note |
|-----------------|------------------------|-----------------------------|------|
| `prod` | `master` | **vuoto** | Riceve `POST /api/sync/edge/` |
| `dev-office` | `replica` | URL master | Pull consigliato dopo deploy master |
| `mirror` | `replica` | URL master | Timer `kor35-mirror-db-sync` sul Pi |
| `dev-home` | `local` | opzionale | DB volume dedicato; sync non obbligatorio |

Endpoint master (path corretto):

```text
https://www.kor35.it/api/sync/edge/
```

Header: `Authorization: EdgeToken <EDGE_SYNC_TOKEN>` (stesso valore su master e replica).

## Stato incrementale (`since`)

Il servizio `backend` monta `../../.runtime-state/` → `/app/runtime-state/` nel container.

File stato per profilo (non committare):

- `edge_sync_dev-home.json`
- `edge_sync_dev-office.json`
- `edge_sync_mirror.json`
- `edge_sync_prod.json` (solo se si lancia sync da container prod)

## Workflow dopo modifiche al codice o al DB

1. **Migrazioni** su tutti i nodi che partecipano al sync (`make migrate ENV=prod`, poi mirror/dev-office).
2. **Deploy backend** sul master prima delle replica (fix LWW/MTI inclusi).
3. **Catalogo staff** (Tessiture, Infusioni, wiki, …): preferire edit sul **master**; su replica usare pull-only se serve allinearsi.
4. Pull DB dalla replica:

```bash
make sync-db ENV=dev-office
# oppure full reset del cursore since:
make sync-db-full ENV=dev-office
```

5. **Media** separati: `make sync-media` / `make sync-media-push` (vedi `.env.sync-media`).

## Modelli MTI (es. `Tessitura`)

Campi sulla tabella figlia (`usa_effetto_temporaneo`, `oggetto_runtime_config`, …) viaggiano nel payload `personaggi.tessitura`. Non editare la stessa `sync_id` su master e replica con timestamp incoerenti: una replica in ritardo non deve più sovrascrivere il master (fix in `kor35/syncing.py`).

Identificare un record: **`sync_id`**, non l’`id` numerico (diverso tra ambienti).

## Comandi utili

```bash
make sync-db ENV=dev-office
make sync-db-diagnose ENV=mirror
make mirror-resync-after-event ENV=mirror
```

Log sync sul master:

```bash
make logs ENV=prod
# cercare: Edge sync failed, edge_sync, IntegrityError
```
