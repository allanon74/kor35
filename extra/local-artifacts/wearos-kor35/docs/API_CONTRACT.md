# API Contract Notes

## Base URL

Valore di default nel codice: `https://www.kor35.it/` (produzione). Per laboratorio si può temporaneamente cambiare in `Kor35ApiConfig` e ricompilare.

## Headers richiesti

- `X-Campagna` (se necessario in base al profilo utente)
- `X-KOR35-Pair-Token` per endpoint protetti device

## Payload evento sync (watch -> server)

```json
{
  "device_id": "wearos-01",
  "firmware_version": "wearos-mvp-0.1.0",
  "events": [
    { "client_event_id": "evt-1", "stat_sigla": "PV", "delta": -1 }
  ]
}
```

## Stat sigla supportate

- `PV`
- `PA`
- `PS` (PG lato UI)
- `CHA`

## Pairing device-side automatico

- `POST /api/personaggi/api/device/watch/pair/start/` -> genera `pairing_code`
- `GET /api/personaggi/api/device/watch/pair/status/?device_id=...&code=...`
  - `pending`: in attesa conferma dalla web app
  - `paired`: ritorna `pair_token` da usare per profile/sync
  - `expired` oppure `invalid`
