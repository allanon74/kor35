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

### `modify_shell`

Assegna o modifica segnalini **Guscio** su un eroe. Il Guscio assorbe un colpo letale (l'eroe resta a 1 PV).

```json
{
  "type": "modify_shell",
  "hero": "this",
  "delta": { "ref": "param.X" },
  "set": true
}
```

| Campo | Valori |
|-------|--------|
| `hero` | `this` (carta/eroe del contesto), `hero_0`, `hero_1` |
| `delta` | Numero o ref; con `set: true` imposta il valore assoluto |
| `set` | Se `true`, sostituisce i segnalini; altrimenti somma |

### `heal_heroes`

Cura PV degli eroi (fino alla Robustezza massima).

```json
{
  "type": "heal_heroes",
  "target": "self_hero",
  "amount": { "ref": "param.X" }
}
```

| `target` | Eroi curati |
|----------|-------------|
| `self_hero` | L'eroe della carta / contesto |
| `own_heroes` | Tutti i tuoi eroi in campo |
| `own_non_exhausted` | I tuoi eroi non esauriti |

`amount`: intero, ref, oppure `"full"` per ripristino completo.

### `sinergia_if_active`

Effetto condizionale: conta i personaggi in campo il cui `testo_gioco` contiene «sinergia» (case insensitive). Se `min_count` (default 2) è raggiunto, applica pesca e/o mana.

```json
{
  "type": "sinergia_if_active",
  "min_count": 2,
  "draw_count": { "ref": "param.X" },
  "draw_target": "self"
}
```

Opzionale `energy_delta` + `energy_target` (`self` \| `opponent`) per bonus mana.

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

## Wizard EffectScript (dashboard staff)

**Dashboard staff → Carte → Keywords → Wizard EffectScript v1**

Workflow consigliato per una nuova keyword con effetto automatico in duello:

1. **Codice e nome** — usa placeholder maiuscoli tra parentesi quadre: `Mutazione [X]`, `Colpo [Y]`.
2. **Testo regola** — ripeti gli stessi `[X]` nel testo mostrato sulla carta.
3. **Ricetta** — nel wizard scegli un template (Mutazione, Colpo, Pesca, Rigenerazione, Ferita, Guscio, Guarigione, Sinergia) oppure «Vuoto» per script custom.
4. **Trigger** — `on_play`, `on_exhaust`, `on_turn_start`, ecc. (deve combaciare con quando vuoi che scatti l’effetto).
5. **Parametri** — il wizard legge `[X]` dal nome e imposta i `default` in `params`.
6. **Valida script** — pulsante che chiama `POST /api/staff/carte/effect-schema/` con `{ script, nome, codice }`.
7. **Salva keyword** — la validazione server ripete gli stessi controlli al salvataggio.

Per passi custom oltre i template: apri **Modifica JSON avanzato** nel wizard.

### Ricette template (API `templates.*`)

| Template | Trigger default | Effetto |
|----------|-----------------|---------|
| `mutazione` | `on_exhaust` | Scelta PG in mano ≤ X, poi `replace` |
| `colpo_influenza` | `on_play` | Danno influenza avversaria |
| `pesca` | `on_turn_start` | Pesca X carte |
| `rigenerazione_energia` | `on_play` | +X energia |
| `danno_eroe` | `on_play` | Scelta eroe avversario, danno salute |
| `guscio` | `on_play` | Assegna X segnalini Guscio all'eroe |
| `guarigione` | `on_turn_end` | Cura X PV a questo personaggio |
| `guarigione_completa` | `on_turn_end` | Ripristina tutti i PV |
| `sinergia_pesca` | `on_turn_start` | Se 2+ Sinergia: pesca X |
| `sinergia_energia` | `on_turn_start` | Se 2+ Sinergia: +X mana |

### Errori comuni

| Errore | Causa | Fix |
|--------|-------|-----|
| `params.X` mancante | Nome `Mutazione [X]` ma script senza `params.X` | Aggiungi param o usa wizard |
| `from_placeholder` errato | `params.X.from_placeholder` ≠ `X` | Allinea al placeholder nel nome |
| `steps` vuoto | Script senza passi | Almeno uno step obbligatorio |
| Trigger non scatta | Evento sbagliato (es. `on_play` su effetto «a inizio turno») | Usa `on_turn_start` |

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
| `modify_shell` (Guscio) | ✅ |
| `heal_heroes` (Guarigione) | ✅ |
| `sinergia_if_active` | ✅ |
| Fasi turno (Apertura / Combattimento / Chiusura) | ✅ |
| Bonus passivi Leader (color pie) | ✅ |
| Compositore staff | ✅ Wizard EffectScript v1 (ricette + validazione) |
| Catena effetti (coda FIFO) | ✅ |
| `player_choice` bersaglio eroe | ✅ |

## API staff utili

| Metodo | URL |
|--------|-----|
| GET | `/api/staff/carte/effect-schema/` — schema + template |
| POST | `/api/staff/carte/effect-schema/` — valida `{ script, nome, codice }` |
| CRUD | `/api/staff/carte/keywords/` — include `effect_script` |

In duello: azione giocatore `effect_choice` con `{ "choice_id", "carta_posseduta_id" }`.

---

*Sorgente: `docs/wiki/carte/effect-script-v1.md` — slug `carte-effect-script-v1`.*
