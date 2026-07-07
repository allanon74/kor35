# 04 — Roadmap Card Arena

## Obiettivo

Client web per **collezione, deck builder e partite** PvP/PvE, ispirato a GCCG ma nativo HTTP/WebSocket.

## Stato attuale KOR35 (da non rompere)

Già implementato in-app:

- `CartaPosseduta`, `MazzoDuello`, `DuelloCarte`
- `carte_duello_service`, `carte_effect_engine`, EffectScript v1
- Lobby prematch (`carte_lobby_service`)
- UI personaggio carte + duello embedded

Card Arena **estrae** questa esperienza in SPA dedicata, leggendo gli stessi modelli + `arena_playable_spec`.

## MVP (Fase 2)

### Funzionalità

- [ ] Login (session KOR35 o token Arena standalone)
- [ ] Collezione filtrata per personaggio / giocatore platform
- [ ] Deck builder 15 carte + leader (`MazzoDuello`)
- [ ] Matchmaking semplice (codice invito, come oggi)
- [ ] Tavolo duello: stato via WebSocket, azioni validate server-side
- [ ] Mobile-first UI + layout desktop

### Backend

- Evolvere `DuelloCarte` verso payload `duel_state_v1` (JSON documentato)
- Endpoint read-only giocatore per `arena_playable_spec` (o derivazione on-the-fly)
- `CarteArenaRuleset` come fonte zone/formato

### Non in MVP

- Ranked ladder globale
- Tornei sealed/draft
- Replay completo partita
- Economia mercato (resta in KOR35 fino a Fase 4)

## Stack consigliato

```
apps/card-arena/
  src/
    pages/Collection.jsx
    pages/DeckBuilder.jsx
    pages/Match.jsx
    hooks/useDuelSocket.js
  vite.config.js             # base: /cardarena/
```

Backend:

- Django Channels o ASGI nativo per WS `/ws/duel/{id}/`
- Stesso worker Gunicorn **non** sufficiente in prod → valutare `daphne` + Redis channel layer

## Contratti

| Contratto | Uso |
|-----------|-----|
| `playable_card_spec_v1` | Definizione carta in partita |
| `arena_deck_spec_v1` | Metadati mazzo |
| `duel_state_v1` | Snapshot tavolo |
| `action_protocol_v1` | Messaggi client → server |
| `event_log_v1` | Storico azioni (replay futuro) |

Dettaglio in `06-contratti-json.md`.

## Identità giocatore

| Modalità | Identità | Collezione |
|----------|----------|------------|
| Standalone Arena | `CartePlatformGiocatore.user` | `CartaPosseduta` legata a profilo PG dedicato o tabella futura |
| KOR35 Bridge | `CartePlatformGiocatore.personaggio` | `CartaPosseduta.personaggio` (esistente) |

Fase 2 bridge-first: Arena richiede `personaggio_id` in query da KOR35.

## Engine effetti

Riusare **integralmente**:

- `personaggi/carte_effect_engine.py`
- `personaggi/carte_effect_script.py`
- Keyword runtime + errata (`CartaErrata`)

Arena invia azioni JSON; server esegue script e restituisce `duel_state_v1` aggiornato.

## Migrazione duello in-app → Arena

1. Fase 2: link «Apri in Card Arena» da scheda personaggio
2. Stesso `DuelloCarte.id` / `sync_id` come chiave partita
3. KOR35 embedded: iframe `/cardarena/match/{id}?char={personaggio_id}`
4. Deprecare UI duello in-app solo quando parità funzionale

## Formati mazzo

`MazzoDuello.formato_codice` + `CarteArenaRuleset.formato_mazzo`:

```json
{
  "version": "1",
  "max_cards": 15,
  "max_duplicates": 2,
  "leader_required": true,
  "banned_tags": []
}
```

Validazione deck builder: stessa logica di `salva_mazzo_duello` oggi, estesa da ruleset.

## Criteri di done Fase 2

- [ ] Partita completa 2 giocatori su WebSocket
- [ ] Deck save/load da `MazzoDuello`
- [ ] EffectScript v1 eseguito server-side
- [ ] Test integrazione `personaggi/tests_carte_collezionabili.py` + nuovi test WS
