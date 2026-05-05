# KOR35 Pilotaggio - Checklist Collaudo Rapido (10 min)

Obiettivo: verificare end-to-end il minigame su Raspberry Pi in modalita kiosk dual-screen.

Tempo stimato: 10 minuti.

## Prerequisiti

- Backend e frontend disponibili in ambiente test.
- Migrazioni applicate.
- Tick server attivo (`pilot_tick --loop --interval 5`).
- Raspberry con due schermi collegati:
  - HDMI principale 16:9 per stato nave.
  - Touchscreen 1920x440 per plancia controllo.

## 0) Bootstrap (1 min)

### Docker-first (raccomandato)

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py pilot_tick --loop --interval 5
```

Se il tick gira in un service separato del compose, verifica solo che sia `Up`.

Nota runtime:
- il servizio `pilot_tick` parte automaticamente con lo stack Docker;
- gli eventi di ticking sono attivi solo durante il viaggio (dopo `Decollo`), fino a `Arrivata` o `Precipitata`;
- fuori dal viaggio il worker resta in idle (impatto risorse minimo);
- dalla console sono disponibili pulsanti manuali `Start Tick` / `Stop Tick` per recovery.

## 1) Verifica apertura URL dual-screen (1 min)

Sul Raspberry (o da browser test):

- `dev-home`: `http://127.0.0.1:8080/pilot/?screen=status` e `http://127.0.0.1:8080/pilot/?screen=control`
- `dev-office`: `http://127.0.0.1:8081/pilot/?screen=status` e `http://127.0.0.1:8081/pilot/?screen=control`
- Oppure host Edge: `http://<HOST_TEST>/pilot/?screen=status|control`

### Esito atteso

- Le due pagine si aprono senza errori.
- Layout coerente con le due risoluzioni.

## 2) Login console via ticket/QR (1 min)

- Apri la console controllo.
- Genera ticket QR.
- Da telefono (utente loggato web app) fai claim ticket.

### Esito atteso

- Console passa da login a sessione attiva.
- Nome pilota visibile in banner.

## 3) Avvio sessione volo (1 min)

- Seleziona partenza/arrivo.
- Avvia viaggio.

### Esito atteso

- Stato sessione passa a `decollo`/`volo` in base alla sequenza.
- Schermo stato mostra rotta, DEFCON e pannelli runtime.

## 4) Test plancia sottosistemi (2 min)

- Dal touch apri 3 sottosistemi di gruppi diversi.
- Imposta livello (0..9) e invia.
- Per `manovra` prova direzione (es. `destra`).
- Prova `inverti effetto` e `espulsione` su uno dei sistemi.

### Esito atteso

- I livelli aggiornano `livello_target` (e `livello_attuale` per generatori con rampa).
- Sottosistema espulso va offline / non regolabile.
- Lo schermo stato riflette i cambiamenti.

## 5) Test energia/carburante/storage (1 min)

- Alza i reattori (`generatore`) e alcuni consumatori.
- Osserva i valori energia.

### Esito atteso

- `produzione_ultimo_tick` e `consumo_ultimo_tick` coerenti coi livelli.
- Se consumo > produzione, cala `storage_energia_attuale`.
- Se a riposo e in surplus, avanza la ricarica storage/carburante secondo coeff.

## 6) Test eventi e allerta (1 min)

- Mantieni sessione attiva almeno 3-4 tick.
- Forza un comando errato per vedere incremento DEFCON.

### Esito atteso

- Eventi compaiono secondo probabilita stato allerta.
- Countdown evento visibile su schermo stato.
- DEFCON aumenta/diminuisce in base a esiti.

## 7) Test QR sabotaggio/riparazione (2 min)

- Scansiona QR sottosistema con PG `0SA > 0`.
- Verifica guasto (offline).
- Scansiona stesso QR con PG `0RI > 0`.

### Esito atteso

- Stato diventa `GUASTO` immediatamente dopo sabotaggio.
- Appare stato `in riparazione` con countdown + barra progresso.
- A fine timer il sottosistema torna online.

## 8) Criteri di accettazione

Il collaudo e considerato positivo se:

- Dual-screen stabile in kiosk.
- Input touch funziona senza lag evidente.
- Runtime tick coerente ogni 5s.
- Eventi/DEFCON/sottosistemi/QR rispondono correttamente.
- Nessun errore bloccante in UI o API.

## Troubleshooting rapido

- Schermo nero kiosk: controlla `systemctl status kor35-kiosk`.
- Nessun evento: verifica `probabilita_evento_per_tick` negli stati allerta.
- Nessun avanzamento runtime: verifica processo `pilot_tick`.
- Touch non risponde: verifica mapping display e driver input del pannello.
