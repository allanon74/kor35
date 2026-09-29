# Runbook Console Pilota (KOR-35)

Console di pilotaggio nave: build separata `frontend-pilot/`, app Django `pilotaggio`, servita da Nginx su `/pilot/` solo dove abilitata. Sync Edge-Master integrata (UUID PK + LWW).

## Architettura

```
Raspberry Pi (kiosk)
  └── browser → /pilot/  (build separata)
                  ↓ /api/pilot/...
              Nginx
                  ↓
              Django (app pilotaggio)
                  ↓
              Postgres (modelli sync-safe)
```

- Frontend pilota: `frontend-pilot/` (React + Vite, base `/pilot/`).
- Backend: `backend/pilotaggio/` (modelli, viste, motore eventi, staff CRUD).
- Nginx: `config/docker/nginx-docker/nginx_conf*/common_locations.snippets` (location `/pilot/`).
- Volume pilot build: `config/docker/nginx-docker/react_build_pilot` montato in `/usr/share/nginx/pilot` su ambienti evento/mirror.
- Feature flag backend: `PILOT_CONSOLE_ENABLED` (default `true` su `raspberry_docker`, `false` altrove).

## Endpoint principali

Tutti relativi (`/api/pilot/...`):

- `GET  /api/pilot/console-enabled/` -> availability della console su ambiente corrente.
- `POST /api/pilot/auth/console-ticket/` -> crea ticket temporaneo per login inverso.
- `GET  /api/pilot/auth/console-ticket/<ticket_id>/claim/?c=<codice>[&personaggio_id=...]` -> claim dal telefono del giocatore autenticato.
- `GET  /api/pilot/auth/console-ticket/<ticket_id>/status/?c=<codice>` -> polling console (pending/authorized/expired).
- `POST /api/pilot/auth/qr-login/` body `{qr_id}` -> endpoint legacy diretto (compatibilita').
- `POST /api/pilot/auth/logout/` (header `Authorization: PilotToken <t>`).
- `GET  /api/pilot/session/state/` -> stato runtime (sessione, evento attivo, sottosistemi, sequenze).
- `GET  /api/pilot/percorsi/` -> rotte attive (partenza, arrivo, distanza minima/massima).
- `GET  /api/pilot/comunicazioni/quadro/` -> evento in corso (senza codici), guasti e protocolli colore. Auth `PilotToken`.
- `POST /api/pilot/session/allarme-equipaggio/` body `{allarme}` -> colore (giallo, rosso, nero, blu, ambra, viola, crociera). Con la console comunicazioni attiva il testo va al dipartimento e l'audio è letto dalla plancia.
- `POST /api/pilot/session/start/` body `{percorso_id}`. La distanza è un intero casuale tra minimo e massimo del percorso.
- `POST /api/pilot/session/command/` body `{codice}` (3 char, ultimo numerico).
- `POST /api/pilot/session/abort/`.
- `GET  /api/pilot/session/history/`.
- `POST /api/pilot/subsystems/qr-action/` body `{qr_id, personaggio_id}` (auth DRF token user) -> guasto `0SA>=1` o ripristino `0RI>=1`.
- `GET  /api/pilot/catalog/` (cataloghi sottosistemi/comandi/intensita + liste codici).
- `GET  /api/pilot/prefetture/`.

Staff (richiede `is_staff`):

- `GET/POST/PUT/DELETE /api/pilot/staff/sottosistemi/`
- `GET/POST/PUT/DELETE /api/pilot/staff/comandi/`
- `GET/POST/PUT/DELETE /api/pilot/staff/intensita/`
- `GET/POST/PUT/DELETE /api/pilot/staff/eventi/`
- `GET/POST/PUT/DELETE /api/pilot/staff/sequenze/`
- `GET /api/pilot/staff/sessioni/`
- `POST /api/pilot/staff/sottosistemi/<id>/associa-a-vista/` body `{a_vista_id}`.

## Regole di gioco implementate

- Codici a 3 caratteri: lettera/cifra + lettera/cifra + cifra.
- Soluzione esatta -> DEFCON -1.
- Soluzione parziale (pattern jolly `_`) -> DEFCON invariato.
- Codice errato/timeout -> DEFCON +1.
- DEFCON > 5 -> stato `crashed`.
- Frequenza/durata eventi crescenti con DEFCON (vedi `engine.py`).
- Sottosistema offline (QR `0SA`): codici col primo carattere relativo falliscono.
- Ripristino sottosistema (QR `0RI`): online dopo `durata_ripristino_secondi` (default 60s).
- Sequenze decollo/atterraggio obbligatorie e configurabili.
- Distanza viaggio: catalogo staff **Pilotaggio → Rotte** (partenza, arrivo, distanza minima, distanza massima). All'avvio si estrae un valore casuale nell'intervallo. La durata pianificata segue la crociera nominale.

## Console comunicazioni

Schermata `/pilot/?screen=comunicazioni` (statistica default `0CO`). Si accende da staff **Pilotaggio → Console di bordo**. Con il flag attivo i pulsanti allarme spariscono dalla plancia di navigazione.

- Destinatari: una **KORP** già presente in **Carriere e KORP** (lì è il dipartimento). Il protocollo (testo e audio) si associa in **Pilotaggio → Comunicazioni**. Ogni colore ha un solo protocollo. Segnaposto `{sottosistema}` e `{evento}`.
- Colori aggiuntivi: **ambra** (riparazione) e **viola** (invasione), oltre a giallo, rosso, nero, blu e crociera. Sull'ambra i sottosistemi offline vengono sempre nominati nel messaggio ai membri e nell'audio di plancia.
- L'audio (`testo_audio`, o l'annuncio standard del colore) esce dagli speaker della console di pilotaggio. Il testo va agli utenti dei personaggi con appartenenza ancora attiva a quella KORP.
- Sull'evento, campo «colore richiesto»: se la radio lo dichiara prima della fine della reazione, il primo controllo di catastrofe non scatta. La radio non vede quel colore. Crociera non dà grazia.

## Comandi operativi (Docker-first)

```bash
# Generare migrazioni e applicarle
make makemigrations MAKEMIGRATIONS_APP=pilotaggio ENV=dev-home
make migrate ENV=dev-home

# Build console pilota e reload Nginx (dev)
make restart-fe-pilot ENV=dev-home

# Avanza il motore manualmente (one-shot)
make pilot-tick ENV=dev-home

# Loop continuo del motore (dev / debug)
docker exec -t kor35_devhome_backend python manage.py pilot_tick --loop --interval 5

# Test
docker exec -t kor35_devhome_backend python manage.py test pilotaggio
```

## Setup iniziale tipico (staff)

1. Configurare le statistiche `0PI`, `0SA`, `0RI` (admin Django, app `personaggi`).
2. Creare `SottosistemaNave` (ognuno con `codice` di 1 char e `a_vista` collegata a un QR).
3. Creare `ComandoNave` per ogni secondo carattere usato.
4. Creare `IntensitaComando` (0..9) per il terzo carattere.
5. Creare `EventoNave` con `codice_soluzione_esatta`, eventuali pattern parziali e `peso_random`.
6. Creare `SequenzaVolo` di tipo `decollo` e `atterraggio`.
7. Generare QR code dal modulo personaggi e associare via staff API.

## Flusso login inverso (operativo)

1. La console apre `POST /api/pilot/auth/console-ticket/`.
2. Mostra QR del link claim.
3. Il giocatore (gia' loggato nella web app) scannerizza il QR e apre il link.
4. Il backend verifica `0PI >= 1` su uno dei personaggi dell'utente (o su `personaggio_id` indicato).
5. La pagina smartphone mostra esito "Console sbloccata" con pulsante di ritorno all'app.
6. La console polla `.../status/` finche' riceve `authorized` con `token`.

## Sync Edge-Master

I modelli pilotaggio sono inclusi automaticamente nella sync registry (vedi `kor35/edge_sync.py`).
Ogni modello e' UUID PK + `created_at`/`updated_at` (LWW). I QR/A_vista riusano l'infrastruttura esistente.

## Deploy

- CI: il workflow `.github/workflows/deploy.yml` builda `frontend-pilot`.
- Produzione: `react_build_pilot` montato in nginx; rsync ad **ogni** deploy (job `build-frontend-pilot` + step rsync in CI).
- Mirror: stesso flusso.
- `PILOT_CONSOLE_ENABLED=true` in `backend/.env.prod` (template aggiornato).
- Nginx: le location `/pilot/` sono disponibili ma operative solo se esiste la build pilot montata.

## Hardening Raspberry kiosk

Sul Raspberry dedicato:

- Avviare Chromium in kiosk mode su `https://<host>/pilot/`.
- Disabilitare combo tastiera che chiudono il browser (es. `xdotool key --clearmodifiers Escape` ignorato).
- L'app cattura tutti i tasti: solo `A-Z`, `0-9`, `Backspace`, `Enter` sono attivi.
- Nessun routing client al di fuori del flusso login -> idle -> cockpit.

## Troubleshooting

- 403 su creazione ticket: verificare `PILOT_CONSOLE_ENABLED=true` nel file env dell'ambiente evento/mirror.
- 404 su `/pilot/`: verificare `react_build_pilot` sul server e `make restart-fe-pilot ENV=prod|mirror`.
- Token console scaduto: l'app rileva 401 e riporta al login QR.
- Backend offline: la console mostra `[OFFLINE LOCALE]` e accumula i comandi in `localStorage` (`kor35_pilot_offline_queue`); al ritorno online tenta automaticamente la sincronizzazione.
