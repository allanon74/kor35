# 03 — Roadmap Card Studio

## Obiettivo

Web app per **progettare, anteprima e stampare** carte KOR35 con workflow simile a Magic Set Editor, senza dipendere dal client desktop MSE.

## MVP (Fase 1)

### Funzionalità

- [ ] Lista espansioni (`EspansioneCarte`) per campagna
- [ ] Editor carta: campi gameplay esistenti + pannello layout (`studio_carta_spec`)
- [ ] Anteprima live con `CardFrame.jsx` esteso (template da `CarteStudioTemplate.layout_spec`)
- [ ] Salvataggio via API staff catalogo (già esistente)
- [ ] Export PNG/PDF per carta e pagina set
- [ ] Un template default per campagna (`bootstrap` API)

### Non in MVP

- Import completo `.mse-set` / scripting MSE
- Editor visuale drag-and-drop layer
- Multi-game per istanza Studio

## Stack consigliato

```
apps/card-studio/
  src/
    pages/SetList.jsx
    pages/CardEditor.jsx
    components/TemplatePreview.jsx
    api/studioClient.js      # wrapper /api/staff/carte/*
  vite.config.js             # base: /cardeditor/
```

Condividere con KOR35:

- `frontend/src/carte/CardFrame.jsx`
- `frontend/src/carte/parseCardRulesText.js`
- Nuovo package `packages/card-studio-core` per validazione JSON

## API da usare (già disponibili)

| Endpoint | Uso Studio |
|----------|------------|
| `GET/POST /api/staff/carte/espansioni/` | Set list |
| `GET/PATCH /api/staff/carte/catalogo/` | Carte |
| `GET/POST /api/staff/carte/platform/gioco/` | Game def |
| `GET/POST /api/staff/carte/platform/templates/` | Template |
| `POST /api/staff/carte/platform/templates/import-mse-style/` | Import package `.mse-style/.zip` |
| `POST /api/staff/carte/platform/gioco/{id}/bootstrap/` | Setup iniziale |

### Import `.mse-style` e gestione file package

L'endpoint `import-mse-style`:

- salva il package originale in `mse_style_package`;
- estrae **tutti** i file (grafici e non) sotto `MEDIA_ROOT/card_studio/mse_styles_extracted/<template_sync_id>/`;
- genera `mse_assets_manifest` con `path`, `size`, `sha256`, `mime`, `asset_type` (`image|text|binary`);
- aggiorna `mse_extracted_root` e `mse_style_riferimento`;
- prova a leggere metadati base dal file `style` (`game`, `card width/height/dpi`) e li riflette in `layout_spec`.

### Import massivo dataset MSE iniziale

Per bootstrap da installazioni MSE esterne.

Sorgente prevista lato host dev (fuori container):

- `~/Scaricati/mse/`
  - `1_*`
  - `2_*`
  - `3_*`
  - `4_*`

Prima del comando, i contenuti sorgente vengono copiati in workspace:

- host: `./.runtime-state/mse_dataset/`
- container backend: `/app/runtime-state/mse_dataset/`

Target make consigliati:

```bash
# Dry-run (nessuna scrittura DB/media)
make import-mse-dataset-dry-run ENV=dev-office CAMPAGNA_SLUG=<slug_campagna>

# Import reale
make import-mse-dataset ENV=dev-office CAMPAGNA_SLUG=<slug_campagna>
```

Comando Django equivalente (se vuoi lanciarlo manualmente):

```bash
docker compose ... exec -T backend python manage.py import_mse_dataset \
  --campagna-slug <slug_campagna> \
  --source-root ~/Scaricati/mse
```

Regola ordine sorgenti: le sottocartelle vengono elaborate per primo carattere numerico
(`1*`, poi `2*`, poi `3*`, poi `4*`...), e i package omonimi successivi fanno **overwrite**.

## Permessi

Capability campagna `editor_carte` (da definire in `CampagnaFeaturePolicy` / ruoli staff). Fase 1: riusare `IsStaffOrMaster` come oggi.

## Flusso utente

1. Staff apre `/cardeditor` (stessa sessione KOR35)
2. Seleziona campagna attiva
3. Sceglie espansione → griglia carte
4. Modifica carta: tab **Gameplay** (campi attuali) + tab **Layout** (`studio_carta_spec`, template)
5. Anteprima → export immagine

## Integrazione campi layout

`studio_carta_spec_v1` (vedi `06-contratti-json.md`):

```json
{
  "version": "1",
  "layers": [
    {"id": "art", "type": "image", "field": "immagine"},
    {"id": "title", "type": "text", "field": "nome"}
  ],
  "print": {"bleed_mm": 3, "safe_mm": 2}
}
```

Il template (`CarteStudioTemplate.layout_spec`) definisce dimensioni e font; la carta può override layer.

## Fase 1.5 — Export MSE subset

- Job `export_mse_set` su `CartePlatformExchangeJob`
- Mapper in `card-studio-core`: KOR35 → file testo MSE (subset campi)
- `mse_campi` su carta per round-trip parziale

## Fase 2 — Import MSE

- Upload `.mse-set` → job `import_mse_set`
- Parsing in worker (Celery o management command)
- Crea/aggiorna `CartaCollezionabile` + popola `mse_campi`
- Conflitti: LWW su `updated_at` (sync edge)

## UI staff attuale

`CarteCollezionabiliManager.jsx` resta operativo. Card Studio **sostituisce gradualmente** la parte layout/stampa; fino ad allora i nuovi campi sono opzionali e nascosti in tab avanzate.

## Criteri di done Fase 1

- [ ] Build deployata sotto `/cardeditor/`
- [ ] CRUD carta + anteprima template default
- [ ] Export PNG singola carta
- [ ] Documentazione utente staff in wiki (`docs/wiki/staff/` se procedure operative)
