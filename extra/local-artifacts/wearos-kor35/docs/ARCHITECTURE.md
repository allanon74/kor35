# Wear OS MVP Architecture

## Obiettivo

App Wear OS che controlla risorse personaggio KOR35 con comportamento offline-first.

## Livelli

1. UI (Compose for Wear OS)
2. Domain (use-case semplici)
3. Data (Retrofit + Room + DataStore)
4. Sync worker (WorkManager)

## Flusso pairing

1. Watch richiede codice (`pair/start`)
2. Giocatore inserisce codice in webapp
3. Watch riceve token/sessione da backend (via `profile` o step dedicato)
4. App salva pair token in DataStore

## Flusso update risorse

1. Tap/long-press in GameScreen crea evento locale
2. UI aggiorna subito il valore locale (optimistic)
3. Evento salvato in queue Room (`pending`)
4. Worker tenta `sync` periodico
5. Se sync ok: evento marcato `sent`, UI riallineata con payload server

## Regola coma

La regola resta lato backend.
La UI watch mostra solo stato/timer ricevuti da `profile` e da risposta `sync`.
