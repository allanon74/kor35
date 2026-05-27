# Migrazione Carriere / KORP unificate (`0181_carriere_unificate`)

## Cosa fa

- Crea `TipoCarriera` (seed: `korp`, `professione`)
- Sposta le 5 KORP da `personaggi_korp` → `personaggi_carriera` (stessi ID tier)
- Promuove ogni **Tier T3** (esclusi segni zodiacali e KORP) a **Carriera** tipo Professione (wiki e `abilita_tier` invariati)
- Unifica `Carica` e `PersonaggioCarrieraMembership`
- `Korp` diventa **proxy** di `Carriera`
- Rimuove i vincoli DB “una KORP / una carriera attiva per PG”

## Ambiente test (sviluppo)

```bash
# Dalla root del progetto, con stack dev attivo (-T = niente prompt interattivo):
docker compose -f config/docker/compose.base.yml -f config/docker/compose.dev-home.yml exec -T backend \
  python manage.py migrate personaggi 0181_carriere_unificate

# Verifica rapida:
docker compose -f config/docker/compose.base.yml -f config/docker/compose.dev-standalone.yml exec backend \
  python manage.py shell -c "
from personaggi.models import Carriera, Korp, TipoCarriera, Tier
print('tipi', list(TipoCarriera.objects.values_list('codice', flat=True)))
print('korps', Korp.objects.count())
print('carriere', Carriera.objects.count())
print('professioni T3', Carriera.objects.filter(tipo_carriera__codice='professione').count())
"
```

Adatta i file `compose.*.yml` al profilo che usi di solito (`dev-home`, `dev-office`, ecc.).

## Produzione e mirror — raccomandazione

**Esegui la migrazione manualmente** nel container backend **subito dopo** il deploy del codice che contiene `0181`, **prima** di servire traffico giocatori se possibile.

Motivo: è una migrazione dati su MTI Django; conviene un solo passaggio controllato, backup DB, e smoke test staff/wiki.

### Checklist prod/mirror

1. **Backup DB** (snapshot o `pg_dump`) sul nodo Master (e mirror se ha DB separato).
2. Deploy immagini/git con questa revisione (backend + frontend build).
3. **Migrazione** (stesso comando `migrate` nel container `backend` del compose prod/mirror).
4. Smoke test:
   - Staff → **Carriere e KORP**: elenco professioni + 5 KORP
   - Wiki: pagina con `{{WIDGET_TIER:…}}` su un tier T3 professione
   - Social: post visibilità KORP
   - API pubblica `GET /api/personaggi/api/korp/` ancora funzionante
5. Se usi **sync edge**: dopo migrate Master, sync verso edge; i tipi carriera e membership viaggiano con `sync_id`.

### Non includere nel deploy automatico senza review

Evita pipeline che lanciano `migrate` su prod senza backup se non è già la prassi del progetto. Per mirror, ripeti migrate sul DB mirror dopo allineamento schema.

## Rollback

Non c’è reverse automatico dei dati. In caso di errore: ripristino backup DB + checkout codice precedente.

## Note staff

- Nuova appartenenza **KORP**: checkbox predefinita “chiudi KORP precedente” (molto consigliata), senza vincolo DB.
- Endpoint staff: `/api/personaggi/api/staff/carriere/`, `…/cariche/`, `…/personaggi-carriere-membership/`

## Migrazione successiva `0182_carriera_tier_sblocco`

Dopo `0181`, applicare anche:

```bash
docker compose … exec backend python manage.py migrate personaggi 0182_carriera_tier_sblocco
```

Aggiunge `CarrieraTierSblocco` (M2M carriera → tier abilità) e filtra le abilità acquistabili in base alle membership attive.

### Test (evitare il blocco su «database already exists»)

Django chiede `yes/no` se il DB `test_kor35_dev` esiste già. Usa **`--keepdb`** e **`exec -T`**:

```bash
docker compose -f config/docker/compose.base.yml -f config/docker/compose.dev-home.yml exec -T backend \
  python manage.py test personaggi.tests_carriere_tier_sblocco gestione_plot.tests_staff_dashboard_layout -v1 --keepdb
```

Per ricreare da zero il DB di test (una tantum):

```bash
docker compose -f config/docker/compose.base.yml -f config/docker/compose.dev-home.yml exec -T db \
  psql -U postgres -c "DROP DATABASE IF EXISTS test_kor35_dev;"
# poi test senza --keepdb, oppure: yes | docker compose ... exec backend python manage.py test ...
```
