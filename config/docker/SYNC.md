# Sincronizzazione DB (Edge sync) e Docker

KOR35 replica dati tra **master** (produzione) e **replica** (dev-office, mirror/Pi) con Last-Write-Wins su `sync_id` + `updated_at`. I file media non passano nel JSON: solo `rsync` (`make sync-media`).

### Rubriche / immagini social

Nel payload sync restano solo i **path relativi** (`hero_immagine`, galleria, logo, …). Sul mirror:

1. Sync DB (~2 min) aggiorna i record.
2. Sync media (`kor35-mirror-media-sync.timer`, ogni ora al minuto `:15`) copia i file sotto `media_data/`.

Il timer esegue `scripts/mirror_media_sync.sh`: **push best-effort** poi **pull obbligatorio**. Se il push verso master fallisce (es. `Permission denied` su directory legacy di proprietà root), il pull da master continua comunque — non usare più `make sync-media-push && make sync-media` nelle unit. Gli script `sync_media_*_wsl_pi_like.sh` trattano rsync exit **23** (trasferimento parziale) come warning, non come fallimento fatale.

Dopo upload di immagini rubriche sul master, se il Pi mostra 404: `make sync-media` sul Pi (o attendere il timer). Diagnostica:

```bash
make check-media ENV=mirror
# oppure tutti i FileField social:
make check-media ENV=mirror CHECK_MEDIA_ALL=1 CHECK_MEDIA_PREFIX=
```

Importante: i path media **non** devono essere riscritti col PK locale al `save()` dopo sync (fix in `normalize_media_field_path`).

Se il DB punta già a path errati (file presenti ma con UUID master diverso):

```bash
make sync-media
make repair-rubriche-media ENV=mirror DRY_RUN=1
make repair-rubriche-media ENV=mirror
make check-media ENV=mirror
```

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

## DateTime nel payload e `save()` dei modelli

Export JSON: i `DateTimeField` diventano stringhe ISO. All’apply vanno riconvertiti **prima** di `update_or_create`/`save()` (`coerce_sync_scalar_value` in `kor35/syncing.py`). Senza conversione, un `save()` che fa aritmetica su datetime (es. `StaffCompito.scadenza - timedelta`) alza `TypeError`, il record resta *defer* e il cursore `since` avanza comunque: i compiti spariscono dal delta e **non tornano** finché non fai un pull completo.

`auto_now_add` su `created_at` ignora il valore remoto in creazione: dopo l’apply si riallinea col payload (`restore_auto_now_add_from_sync`). Altrimenti gli eventi runtime di pilotaggio (`EventoAttivoSessione`) sul mirror hanno `created_at` = istante sync e `deadline_at` originale, quindi countdown di migliaia di secondi (o negativi).

Recupero dopo il fix (sul nodo replica, **dopo** il deploy del backend):

```bash
make sync-db-full ENV=mirror
# oppure da PC: make mirror-pi-pull  poi sul Pi:
# make sync-db-full ENV=mirror
```

Sintomo nei log: `gestione_plot.staffcompito: TypeError: unsupported operand type(s) for -: 'str' and 'datetime.timedelta'`.

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
