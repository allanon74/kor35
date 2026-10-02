# Design — Tasks (Missioni) + Prestigio

## Prestigio
- Punteggio del personaggio: `Personaggio.prestigio` (ex `peso_influencer`), default **0**, mai negativo.
- Modificabile dallo staff in **Dashboard staff → Personaggi** (lista con colonna Prestigio, dettaglio con campo editabile) e dalla scheda personaggio staff.
- Peso social su post, commenti e like InstaFame: `social.influencer.get_peso_social` = Prestigio con minimo 1.
- Fonti del punteggio: staff, **partecipazione evento** (`Evento.prestigio_base_inizio_evento`, default 0), **ricompense task**.
- **Cariche, carriere e KORP non assegnano Prestigio**: le KORP agiscono solo come moltiplicatore sulle task (vedi sotto).
- Ledger movimenti Prestigio → **v2** (oggi: riga in `PersonaggioLog` a ogni variazione).

## Modelli
- `Missione` (UUID, Syncable): korp opzionale, Cr/Pr, tipo risoluzione, solo-primo, malus/bonus, **`esclusiva`**, eventi M2M.
- `MissioneEvento`, `MissioneRisoluzione` (unique missione+evento+personaggio).
- `Carriera.fattore_task_crediti` e `Carriera.fattore_task_prestigio` (solo KORP, indipendenti tra loro).

## Regole
- Tutti possono fare tutte le task **salvo `esclusiva=True`** (solo membri della KORP).
- Fattori KORP solo sulle task di quella KORP (per membri): Crediti × `fattore_task_crediti`, Prestigio × `fattore_task_prestigio`.
- `fattore_task_prestigio = 0` → la KORP non dà Prestigio sulle proprie task (i Crediti restano moltiplicati dal loro fattore).
- `premio_solo_primo`: dopo la prima risoluzione sparisce dalle effettuabili altrui.
- Claim **automatico** alla risoluzione + **Messaggio** di notifica.
- Assegnazione risoluzione: **Master e Staffer**.

## Riepilogo evento (per ogni KORP X)
1. Cr di Korp = Σ task KORP X × `fattore_task_crediti` di X; Pr di Korp = Σ task KORP X × `fattore_task_prestigio` di X
2. Cr/Pr non di Korp = Σ task generiche + task di altre KORP **non esclusive** (senza fattori)

## Visibilità giocatore
- Tab dedicata **Tasks** nel menu app (modulo campagna `tasks` in TEST/OPEN), **solo mentre un evento è ufficialmente in corso** (`started_at` valorizzato e `ended_at` nullo) **e il personaggio è iscritto** (`Evento.partecipanti`).
- Contenuto: task dell'evento **attive** (`MissioneEvento.attiva`, default True all'inizio), **non esclusive**, più le **esclusive della propria KORP**.
- Task disattiva per l'evento: invisibile ai PG e **non** segnabile come risolta.

## Attivazione per evento
- In creazione/modifica, per ogni evento collegato: opzione **Attiva all'inizio** (default sì).
- Durante l'evento (e prima): staff/master possono accendere/spegnere dal pannello Tasks o da Plot → Evento.

## Premio avvio evento
- Oltre a PC e Crediti base: **`prestigio_base_inizio_evento`** (Integer, default 0, può essere negativo).
