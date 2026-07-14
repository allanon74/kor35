# KOR35 — template MSE e allineamento stylesheet (runbook prod)

Runbook per installare il template **`kor35-standard`** e rigenerare `layout_spec.mse_v1` sui template già importati dal dataset MSE.

## Prerequisiti

1. **Codice deployato su prod** che include:
   - `backend/personaggi/mse_kor35_style.py`
   - `management/commands/bootstrap_kor35_mse_template.py`
   - Card Studio frontend aggiornato (preview + tab MSE)
2. **Migrazioni** già applicate su master (`make migrate ENV=prod` o deploy CI).
3. Esiste un `CarteGiocoDefinizione` con `modello_base=kor35` e slug **`kor35`** (su dev-office è l’unico gioco KOR35).
4. **Non** usare slug di test tipo `sette-elegie` — esiste solo nei test automatici.

## Cosa fa il bootstrap

| Step | Effetto |
|------|---------|
| Merge `meta.mse_game_spec` | Campi card/set/pack KOR35 sul gioco |
| Crea/aggiorna `kor35-standard` | Package `.mse-style` con 13 card styles + PNG cornice |
| `--set-default` | Default nuove carte → `kor35-standard` |
| Refresh layout | Rilegge file `style` estratti → `layout_spec.mse_v1` (457 template su dev-office) |
| `campi_schema` | Solo template con `game: kor35` (0 su dataset MTG-only: **normale**) |
| `--link-expansions` | Espansioni KOR35 senza template default → `kor35-standard` |

## dev-office / replica — comandi (già validati)

```bash
# 1) Anteprima (nessuna scrittura DB)
make bootstrap-kor35-mse-template-dry-run ENV=dev-office CAMPAGNA_SLUG=kor35

# 2) Installazione reale
make bootstrap-kor35-mse-template ENV=dev-office CAMPAGNA_SLUG=kor35

# Gioco KOR35 esplicito (slug reale nel DB)
make bootstrap-kor35-mse-template ENV=dev-office CAMPAGNA_SLUG=kor35 GIOCO_SLUG=kor35
```

Equivalente Docker:

```bash
cd config/docker
export KOR35_BACKEND_ENV_FILE=/path/to/backend/.env.dev-office
docker compose -f compose.base.yml -f compose.dev-office.yml exec -T backend \
  python manage.py bootstrap_kor35_mse_template \
  --campagna-slug kor35 --set-default --link-expansions
```

### Output atteso (successo)

```text
Gioco: meta.mse_game_spec KOR35 aggiornato.
Template creato: kor35-standard   # oppure "Template esistente" al secondo run
Import MSE: 3 asset, 13 card styles, root=card_studio/mse_styles_extracted/<uuid>
Default nuove carte → kor35-standard
Template allineati: layout refresh=<N>, campi_schema=<0 se solo MTG>
Bootstrap KOR35 MSE template completato.
```

## Produzione (DigitalOcean) — quando decidi di allineare

### 1. Deploy codice

Merge su `main` → CI deploy su prod (migrate + collectstatic + build frontend).

Verifica che il comando esista nel container:

```bash
ssh -o BatchMode=yes kor35-prod 'cd /srv/kor35/config/docker && \
  COMPOSE_PROJECT_NAME=kor35-prod \
  KOR35_BACKEND_ENV_FILE=/srv/kor35/backend/.env.prod \
  docker compose -f compose.base.yml -f compose.prod.yml exec -T backend \
  python manage.py help bootstrap_kor35_mse_template'
```

### 2. Dry-run su prod (obbligatorio)

```bash
ssh -o BatchMode=yes kor35-prod 'cd /srv/kor35 && \
  make bootstrap-kor35-mse-template-dry-run ENV=prod CAMPAGNA_SLUG=kor35'
```

Oppure Makefile equivalente dalla root repo sul server:

```bash
cd /srv/kor35/config/docker
COMPOSE_PROJECT_NAME=kor35-prod \
KOR35_BACKEND_ENV_FILE=/srv/kor35/backend/.env.prod \
docker compose -f compose.base.yml -f compose.prod.yml exec -T backend \
  python manage.py bootstrap_kor35_mse_template \
  --campagna-slug kor35 --dry-run
```

Controlla:

- Gioco trovato: `kor35 / kor35` (o il tuo slug gioco reale)
- Numero refresh coerente con i template importati
- Nessun errore Python

### 3. Esecuzione reale (finestra breve, idempotente)

```bash
ssh -o BatchMode=yes kor35-prod 'cd /srv/kor35 && \
  make bootstrap-kor35-mse-template ENV=prod CAMPAGNA_SLUG=kor35'
```

Il comando è **idempotente**: rieseguirlo aggiorna `kor35-standard` e riallinea i layout.

Durata indicativa: proporzionale al numero di template (~500 stili ≈ pochi minuti, worker Gunicorn non bloccato — è CLI).

### 4. Verifica post-bootstrap

```bash
ssh -o BatchMode=yes kor35-prod 'cd /srv/kor35/config/docker && \
  COMPOSE_PROJECT_NAME=kor35-prod \
  KOR35_BACKEND_ENV_FILE=/srv/kor35/backend/.env.prod \
  docker compose -f compose.base.yml -f compose.prod.yml exec -T backend \
  python manage.py shell -c "
from personaggi.carte_platform_models import CarteStudioTemplate, CarteGiocoDefinizione
from personaggi.models import Campagna
c = Campagna.objects.get(slug=\"kor35\")
g = CarteGiocoDefinizione.objects.get(campagna=c, slug=\"kor35\")
t = CarteStudioTemplate.objects.get(campagna=c, gioco_definizione=g, slug=\"kor35-standard\")
mse = (t.layout_spec or {}).get(\"mse_v1\") or {}
print(\"styles\", len(mse.get(\"card_styles\") or {}), \"default\", t.is_default_for_new_cards)
"'
```

Atteso: `styles 13 default True`.

### 5. Card Studio (smoke test manuale)

1. Apri `https://www.kor35.it/cardeditor/` (staff, campagna kor35).
2. **Refresh** dati.
3. Tab **Style** → compare **KOR35 Standard** (`kor35-standard`).
4. Tab **Cards** → gioco **kor35**, stylesheet **KOR35 Standard**, preview con name/rules/stats.
5. Tab **Style** su un template MTG importato (es. `modern-style`) → preview MTG (campi diversi dal gioco KOR35).

### 6. Replica / mirror Pi (dopo prod)

I template sono nel DB master. Sul mirror:

```bash
make sync-db ENV=mirror
# oppure dev-office replica
make sync-db ENV=dev-office
```

I file media sotto `card_studio/mse_styles_extracted/` vanno sincronizzati se mancano preview:

```bash
make sync-media ENV=mirror
```

## Comandi opzionali (solo se serve)

```bash
# Solo rigenerare mse_v1 da file style estratti (senza creare kor35-standard)
python manage.py refresh_mse_style_layouts --campagna-slug kor35

# Riallineare gioco_definizione template ↔ game: nel file style
python manage.py normalize_mse_game_links --campagna-slug kor35

# Solo meta.mse_game_spec sui giochi kor35
python manage.py bootstrap_kor35_card_games --campagna-slug kor35
```

## API alternativa (singolo gioco)

```http
POST /api/personaggi/api/staff/carte/platform/gioco/{uuid}/bootstrap/
Content-Type: application/json

{"install_mse_template": true}
```

Installa `kor35-standard` e lo imposta default (senza refresh massivo degli altri 400+ template MTG).

## Interpretazione log

| Messaggio | Significato |
|-----------|-------------|
| `layout refresh=457` | Template con `style` estratto → `mse_v1` ricalcolato |
| `campi_schema=0` | Nessun template con `game: kor35` oltre a quello creato (MTG resta su gioco `magic`) |
| `refresh foo: card_styles=0` | Parser non ha estratto layer (style vuoto, formato non standard, o sezione senza `field:`) — preview Card Studio non disponibile per quello stile |
| `Espansioni collegate: 0` | Tutte le espansioni avevano già un default, o nessuna espansione KOR35 senza template |
| `Gioco non trovato: sette-elegie` | Slug inesistente nel DB — usare `kor35` |

## Template con `card_styles=0` (dev-office)

Circa 20 stili (es. `magic`, `adventure`, `bgg`) — noti limiti parser o file `style` minimali. Non bloccano KOR35: usa **`kor35-standard`** per le carte catalogo KOR35 e gli stylesheet MTG collegati al gioco **`magic`** per sperimentazione cross-game.

## Rollback

Non c’è migrazione DB distruttiva. In caso di problemi:

1. Imposta un altro template come default da admin/API.
2. Disattiva `kor35-standard` (`attivo=false`) se necessario.
3. I layout refreshati sono deterministiche dal file `style` estratto — rieseguire refresh dopo fix parser.

## Checklist rapida prod

- [ ] Codice con `bootstrap_kor35_mse_template` deployato
- [ ] `migrate` prod OK
- [ ] Dry-run prod OK
- [ ] Bootstrap reale prod OK
- [ ] Shell: `kor35-standard` → 13 styles
- [ ] Card Studio smoke test
- [ ] `sync-db` (+ `sync-media` se serve) su mirror/replica
