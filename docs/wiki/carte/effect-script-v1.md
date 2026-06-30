# EffectScript v1 — vocabolario (staff)

> Pagina **solo master**. Riferimento tecnico per il campo `effect_script` sulle keyword.
> Schema machine-readable: `GET /api/staff/carte/effect-schema/` o file repo `backend/personaggi/carte_effect_schema.json`.

## Versione

Tutti gli script devono avere `"version": 1`.

## Struttura radice

```json
{
  "version": 1,
  "params": { "X": { "type": "int", "from_placeholder": "X", "default": 0 } },
  "trigger": { "event": "on_exhaust", "source": "this" },
  "steps": [ ]
}
```

| Campo | Descrizione |
|-------|-------------|
| `params` | Parametri collegati ai placeholder `[X]` del **nome keyword** |
| `trigger` | Quando si avvia la catena di passi |
| `steps` | Passi eseguiti in ordine (server) |

## Parametri (`params`)

Ogni chiave deve corrispondere a un placeholder nel nome keyword (es. `Mutazione [X]` → `params.X`).

| Campo | Valori |
|-------|--------|
| `type` | `int` \| `string` |
| `from_placeholder` | Lettera del placeholder (`X`, `Y`, …) |
| `default` | Valore se il testo carta non cattura il parametro |

Riferimenti nei passi: `{ "ref": "param.X" }`.

## Trigger (`trigger.event`)

| Evento | Quando (MVP / pianificato) |
|--------|----------------------------|
| `on_play` | Carta messa in gioco dal controller |
| `on_exhaust` | Personaggio/eroe si esaurisce (lascia il campo) |
| `on_attack` | Dopo un attacco dichiarato |
| `on_turn_start` | Inizio turno del controller |
| `on_turn_end` | Fine turno del controller |
| `manual` | Solo su azione esplicita (staff / debug) |

`source`: `this` (carta che ha la keyword), `self`, `opponent`.

## Passi (`steps[]`)

### `player_choice` — scelta giocatore

```json
{
  "type": "player_choice",
  "id": "replacement",
  "prompt": "Scegli un Personaggio dalla mano con costo ≤ {X}",
  "optional": true,
  "min": 0,
  "max": 1,
  "filter": {
    "target": "card",
    "zone": "hand",
    "owner": "controller",
    "card_type": "PG",
    "cost_play_lte": { "ref": "param.X" }
  }
}
```

**Scelta carta** (`filter.target`: `card`, default): come sopra.

**Scelta eroe** (`filter.target`: `hero`):

```json
{
  "type": "player_choice",
  "id": "bersaglio",
  "prompt": "Scegli un eroe avversario",
  "filter": {
    "target": "hero",
    "owner": "opponent",
    "occupied": true
  }
}
```

| Campo filtro | Valori |
|--------------|--------|
| `target` | `card` (default) \| `hero` |
| `zone` | `hand`, `field`, `deck`, `discard` (solo `card`) |
| `owner` | `controller`, `opponent`, `self`, `any` |
| `occupied` | solo `hero`: se `true`, solo slot con eroe in campo |

Risposta API duello: `effect_pending.choice_kind` = `card` \| `hero`; per gli eroi usa `eligible_hero_targets[]` con `target` (`opponent_hero_0`, …), `label`, `carta_posseduta_id`.

Azione giocatore `effect_choice`: `{ "choice_id", "carta_posseduta_id" }` oppure `{ "choice_id", "hero_target" }`.

Passi successivi possono usare `{ "ref": "choice.bersaglio" }` come `deal_damage.target`.

### `replace` — sostituisci sul campo

```json
{
  "type": "replace",
  "slot": "this",
  "with": { "ref": "choice.replacement" },
  "skip_if_no_choice": true
}
```

| `slot` | Significato |
|--------|-------------|
| `this` | Slot dell’eroe in esaurimento (`context.hero_slot`) |
| `hero_0` / `hero_1` | Slot eroe proprio |
| `location` | Slot luogo |

### `modify_energy`

`target`: `self` \| `opponent` — `delta`: numero o ref.

### `modify_influence`

Modifica influenza duello (PG «vita»). `delta` negativo = danno.

### `deal_damage`

`target`: `opponent_influence`, `hero_0`, `hero_1`, `opponent_hero_0`, `opponent_hero_1`.

### `draw_cards`

Pesca dal mazzo verso la mano. `count`: numero o ref; `target`: `self` | `opponent`.

### `move_card`

Sposta carta tra zone (`from` / `to`); opzionale `field_slot` se destinazione campo.

## Riferimenti (`ref`)

| Pattern | Esempio |
|---------|---------|
| `param.X` | Valore da keyword / testo carta |
| `choice.<id>` | Carta scelta in uno step `player_choice` |
| `context.<chiave>` | Contesto evento (es. `hero_slot`) |

## Catena di effetti (FIFO)

Quando più keyword con lo stesso `trigger.event` compaiono sullo stesso testo carta, oppure su più carte in campo (es. `on_turn_start`), il server le **accoda tutte** in `stato_gioco.effect_queue` e le risolve **una alla volta** nell’ordine:

1. **Ordine nel testo** — occorrenze lette da sinistra a destra (`iter_keyword_matches`).
2. **Ordine carte in campo** — eroi (slot 0, 1), luogo, oggetti equipaggiati; per ogni carta, tutte le keyword dell’evento.
3. **Priorità keyword** — a parità di posizione nel matcher, keyword con `priorita` più alta vince il match sovrapposto (come per il parsing testo).

Regole:

- Se un effetto richiede `player_choice`, il turno resta in pausa finché il controller non risponde (`effect_choice`); gli effetti successivi in coda attendono.
- Al termine di uno script (o dopo la scelta), il server avanza automaticamente al successivo in coda.
- L’API duello espone `effect_queue_depth` (>1) quando ci sono effetti in attesa oltre a quello corrente.

Esempio testo evento: `Colpo 1. Colpo 2.` → due script `on_play` in sequenza (−1 e −2 influenza).

## Esempio canonico: Mutazione [X]

Template disponibile in API staff (`templates.mutazione`) e pulsante nel tab Keywords.

```json
{
  "version": 1,
  "params": {
    "X": { "type": "int", "from_placeholder": "X", "default": 0 }
  },
  "trigger": { "event": "on_exhaust", "source": "this" },
  "steps": [
    {
      "type": "player_choice",
      "id": "replacement",
      "prompt": "Scegli un Personaggio dalla mano con costo gioco ≤ {X}",
      "optional": true,
      "min": 0,
      "max": 1,
      "filter": {
        "zone": "hand",
        "owner": "controller",
        "card_type": "PG",
        "cost_play_lte": { "ref": "param.X" }
      }
    },
    {
      "type": "replace",
      "slot": "this",
      "with": { "ref": "choice.replacement" },
      "skip_if_no_choice": true
    }
  ]
}
```

## Dove si salva

**Dashboard staff → Carte → Keywords → campo Effect script (JSON)**.

Validazione al salvataggio: schema JSON + allineamento placeholder ↔ `params`.

## Stato implementazione

| Funzione | Stato |
|----------|--------|
| Schema + validazione API | ✅ |
| Campo `effect_script` su keyword | ✅ |
| Motore: `player_choice`, `replace`, danno/energia/influenza | ✅ MVP |
| Trigger automatico `on_exhaust` in duello | ✅ (attacco su eroe nemico) |
| Trigger `on_play` / `on_attack` | ✅ |
| Trigger `on_turn_start` / `on_turn_end` (carte in campo) | ✅ |
| Salute eroi in duello live | ✅ |
| `draw_cards` | ✅ |
| `deal_damage` su eroi (slot) | ✅ |
| `move_card` (hand/deck/discard/field) | ✅ MVP |
| Compositore staff | ✅ Mutazione, Colpo, Pesca, Rigenerazione, Ferita (eroe) |
| Catena effetti (coda FIFO) | ✅ |
| `player_choice` bersaglio eroe | ✅ |

## API staff utili

| Metodo | URL |
|--------|-----|
| GET | `/api/staff/carte/effect-schema/` — schema + template Mutazione |
| CRUD | `/api/staff/carte/keywords/` — include `effect_script` |

In duello: azione giocatore `effect_choice` con `{ "choice_id", "carta_posseduta_id" }`.

---

*Sorgente: `docs/wiki/carte/effect-script-v1.md` — slug `carte-effect-script-v1`.*
