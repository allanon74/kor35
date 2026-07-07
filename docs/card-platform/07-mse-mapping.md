# 07 — Mapping MSE ↔ KOR35

## Approccio

**Clean-room / spec-based.** Non copiare codice GPL da Magic Set Editor 2. Usare `external/MagicSetEditor2` solo come riferimento formato.

Fase export: **subset** sufficiente per stampa e scambio set con community MSE.

## Triangolo package

| Package MSE | Destinazione KOR35 |
|-------------|-------------------|
| `.mse-game` | `CarteGiocoDefinizione` + keyword globali |
| `.mse-style` | `CarteStudioTemplate` (`mse_style_riferimento`, `layout_spec`) |
| `.mse-set` | `EspansioneCarte` + carte |

## Campi carta

| Campo MSE (tipico) | KOR35 | Note |
|--------------------|-------|------|
| `card_name` | `nome` | |
| `card_code` | `codice` | |
| `rule_text` | `testo_gioco` | keyword expand diversa |
| `flavor_text` | `testo_lore` | |
| `card_type` | `tipo` | mapping tabella custom |
| `mana_cost` | `costo_gioco` | 0–3 |
| `power` / `toughness` | `attacco` / `salute` | |
| `card_image` | `immagine` | path relativo, rsync media |
| custom fields | `mse_campi` | round-trip |

Tutto ciò che non mappa 1:1 resta in `mse_campi` JSON.

## Keyword

| MSE | KOR35 |
|-----|-------|
| `keyword_definition` script | `KeywordCarta` + `mse_match_pattern` |
| `reminder_text` | `mse_reminder_template` o `reminder_breve` |
| `expand_keywords` | `parseCardRulesText.js` (logica diversa) |

`mse_export_mode`:

- `kor35` — nessun export keyword verso MSE
- `mse_compat` — genera definizioni MSE semplificate
- `both` — mantiene entrambe le rappresentazioni

## Import job (`import_mse_set`)

Pipeline futura:

1. Upload zip → storage `media/mse_imports/{job_id}/`
2. Parser in `packages/card-studio-core` (no GPL)
3. Per ogni carta: upsert `CartaCollezionabile` by `codice` o nuovo UUID
4. Popola `mse_campi`, collega `espansione`
5. `updated_at` LWW su conflitto sync

## Export job (`export_mse_set`)

1. Query `EspansioneCarte` + carte
2. Applica `campi_schema` mapping
3. Genera file testo + immagini symlink/copy
4. Zip scaricabile; registra su `CartePlatformExchangeJob.risultato`

## Limitazioni note subset v1

- Nessuno scripting MSE `styling`/`script` completo
- Nessun `automatic_card_numbering` MSE avanzato
- Layer template: mapping fisso KOR35 `CardFrame`, non renderer MSE

## Test import/export

- Fixture minima `.mse-set` in `backend/personaggi/fixtures/mse_sample/`
- Test round-trip: export → import → confronto `sync_id` e campi gameplay
