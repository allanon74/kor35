# 06 — Contratti JSON

Versioni centralizzate in `backend/personaggi/carte_platform_specs.py`.

## `playable_card_spec_v1`

Campo: `CartaCollezionabile.arena_playable_spec`

```json
{
  "version": "1",
  "source": "kor35",
  "espansione_slug": "caduta-del-consiglio",
  "gameplay": {
    "codice": "ST-KAEL-001",
    "nome": "Kael",
    "tipo": "PG",
    "energia": "MAR",
    "rarita": "COM",
    "costo_gioco": 2,
    "attacco": 3,
    "salute": 4,
    "iniziativa": 2,
    "testo_gioco": "…",
    "legale_duello": true,
    "bandita": false,
    "duplicabile": false,
    "layout_versione": "STD"
  },
  "keywords": [],
  "effects": []
}
```

Generazione: `build_playable_spec_from_carta(carta)` o job `export_playable`.

**Regola:** se `arena_playable_spec` è vuoto, Arena può derivare al volo dalla carta + errata attiva.

---

## `studio_card_spec_v1`

Campo: `CartaCollezionabile.studio_carta_spec`

```json
{
  "version": "1",
  "layers": [],
  "print": {"bleed_mm": 3, "safe_mm": 2},
  "artist": "",
  "collector_number": ""
}
```

---

## `studio_set_spec_v1`

Campo: `EspansioneCarte.studio_set_spec`

```json
{
  "version": "1",
  "symbol": null,
  "watermark": null,
  "numbering": "CODICE"
}
```

---

## `studio_layout_spec_v1`

Campo: `CarteStudioTemplate.layout_spec`

```json
{
  "version": "1",
  "width_mm": 63,
  "height_mm": 88,
  "dpi": 300,
  "fonts": {},
  "default_layers": []
}
```

---

## `studio_field_map_v1`

Campo: `CarteStudioTemplate.campi_schema`

```json
{
  "version": "1",
  "mapping": {
    "card_name": "nome",
    "mana_cost": "costo_gioco",
    "rule_text": "testo_gioco"
  }
}
```

---

## `arena_deck_spec_v1`

Campo: `MazzoDuello.arena_deck_spec`

```json
{
  "version": "1",
  "formato": "standard_15",
  "sideboard": [],
  "notes": ""
}
```

---

## `arena_ruleset_spec_v1`

Campi su `CarteArenaRuleset`: `zones_spec`, `win_conditions`, `formato_mazzo`

### zones_spec

```json
{
  "version": "1",
  "zones": ["deck", "hand", "field", "reliquary", "graveyard", "exile"]
}
```

### win_conditions

```json
{
  "version": "1",
  "type": "leader_hp_zero"
}
```

---

## `duel_state_v1` (futuro)

Non ancora persistito come colonna dedicata; evolvere `DuelloCarte` o tabella `DuelloCarteState`.

```json
{
  "version": "1",
  "duel_id": "uuid",
  "phase": "main",
  "active_player": "p1",
  "players": {
    "p1": {"leader_hp": 20, "zones": {}},
    "p2": {"leader_hp": 18, "zones": {}}
  },
  "stack": [],
  "turn": 3
}
```

---

## `action_protocol_v1` (futuro)

Messaggio client → server:

```json
{
  "version": "1",
  "action": "play_card",
  "payload": {
    "carta_posseduta_id": "uuid",
    "target": null
  }
}
```

Risposta: `{ "ok": true, "duel_state": { … }, "events": [ … ] }`

---

## `event_log_v1` (futuro)

```json
{
  "version": "1",
  "events": [
    {"seq": 1, "type": "card_played", "at": "ISO8601", "data": {}}
  ]
}
```

---

## Versioning

- Incrementare `version` stringa nel JSON a breaking change
- `CarteGiocoDefinizione.platform_version` traccia bundle contratti supportati
- Backend rifiuta azioni con `version` non supportata (HTTP 400)
