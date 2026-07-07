# 02 — Allineamento database

## Modelli nuovi (`carte_platform_models.py`)

### `CarteGiocoDefinizione`

Radice per campagna (1:1 con `Campagna`). Contiene flag `studio_abilitato`, `arena_abilitata`, `platform_version`, `mse_game_name`.

**Quando crearlo:** prima di abilitare Card Studio o Arena per una campagna con carte collezionabili.

### `CarteStudioTemplate`

Equivalente **style** MSE: `layout_spec`, `campi_schema`, `mse_style_riferimento`.

### `CarteArenaRuleset`

1:1 con `CarteGiocoDefinizione`. Zone, condizioni vittoria, formato mazzo, versione EffectScript.

### `CartePlatformGiocatore`

Bridge identità:

- KOR35: `personaggio` OneToOne + `user` opzionale
- Standalone futuro: `user` + `external_player_ref`

Collezione resta su `CartaPosseduta.personaggio`.

### `CartePlatformExchangeJob`

Audit import/export MSE e job batch (es. rigenerazione `arena_playable_spec`).

---

## Estensioni modelli esistenti

### `EspansioneCarte`

| Campo | Tipo | Uso futuro |
|-------|------|------------|
| `gioco_definizione` | FK | Collegamento al game container |
| `studio_set_spec` | JSON | Metadati set (simbolo, watermark, numbering) |
| `mse_set_riferimento` | string | Path/id package `.mse-set` |

### `CartaCollezionabile`

| Campo | Tipo | Uso futuro |
|-------|------|------------|
| `studio_template` | FK | Template visivo Card Studio |
| `studio_carta_spec` | JSON | Layer stampa extra |
| `arena_playable_spec` | JSON | Snapshot normalizzato per Arena |
| `mse_campi` | JSON | Round-trip import MSE |

**Regola:** i campi gameplay attuali (`costo_gioco`, `effect_scripts`, …) restano autoritativi. `arena_playable_spec` è una **vista materializzata** rigenerabile (job `export_playable`).

### `KeywordCarta`

| Campo | Uso |
|-------|-----|
| `mse_match_pattern` | Pattern export MSE |
| `mse_reminder_template` | Reminder text MSE |
| `mse_export_mode` | `kor35` / `mse_compat` / `both` |

### `MazzoDuello`

| Campo | Uso |
|-------|-----|
| `formato_codice` | Es. `standard_15` |
| `arena_deck_spec` | Metadati sideboard, note formato |

---

## Mapping concettuale → implementazione futura

```
CartaCollezionabile (catalogo)
    ├── studio_carta_spec + studio_template  → Card Studio render
    ├── arena_playable_spec                  → Card Arena engine
    └── effect_scripts                       → già usato da duello KOR35

CartaPosseduta (istanza)
    └── resta l'istanza in collezione / mazzo

EspansioneCarte
    └── studio_set_spec + bustine esistenti  → economy + set editor
```

## Migrazione dati esistenti

Nessuna migrazione dati obbligatoria alla Fase 0:

1. Campi JSON default `{}` — editor attuale ignora
2. Creare `CarteGiocoDefinizione` per campagna quando serve
3. `POST …/bootstrap/` crea template + ruleset default
4. Job `export_playable` popola `arena_playable_spec` da campi gameplay

## Serializer / API staff

Campi platform esposti negli stessi endpoint catalogo:

- `EspansioneCarteSerializer` — `gioco_definizione`, `studio_set_spec`, `mse_set_riferimento`
- `CartaCollezionabileSerializer` — `studio_*`, `arena_playable_spec`, `mse_campi`
- `KeywordCartaSerializer` — campi `mse_*`

Endpoint dedicati platform: `/api/staff/carte/platform/…`

## Test sync

Verificare presenza nel registry:

```python
from kor35.sync_tombstone import get_sync_model_registry
registry = get_sync_model_registry(("personaggi",))
assert "personaggi.cartegiocodefinizione" in registry
```

## Checklist nuovo campo platform

1. Aggiungere al modello con default non-breaking
2. Migrazione su tutti i nodi
3. Serializer staff (opzionale read-only in API giocatore)
4. Documentare in `06-contratti-json.md` se JSON strutturato
5. Test apply sync se modello nuovo
