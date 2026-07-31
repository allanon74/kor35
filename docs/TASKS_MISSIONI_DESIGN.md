# Design — Tasks (Missioni) + Prestigio

## Prestigio
- Rename UI di «Peso social» / `peso_influencer` → **Prestigio**.
- Campo DB invariato; like InstaFame invariati.
- Ricompense task incrementano Prestigio.
- Ledger movimenti Prestigio → **v2**.

## Modelli
- `Missione` (UUID, Syncable): korp opzionale, Cr/Pr, tipo risoluzione, solo-primo, malus/bonus, **`esclusiva`**, eventi M2M.
- `MissioneEvento`, `MissioneRisoluzione` (unique missione+evento+personaggio).
- `Carriera.fattore_task` (solo KORP).

## Regole
- Tutti possono fare tutte le task **salvo `esclusiva=True`** (solo membri della KORP).
- Fattore KORP solo sulle task di quella KORP (per membri).
- `premio_solo_primo`: dopo la prima risoluzione sparisce dalle effettuabili altrui.
- Claim **automatico** alla risoluzione + **Messaggio** di notifica.
- Assegnazione risoluzione: **Master e Staffer**.

## Riepilogo evento (per ogni KORP X)
1. Cr/Pr di Korp = Σ task KORP X × fattore_X  
2. Cr/Pr non di Korp = Σ task generiche + task di altre KORP **non esclusive** (senza fattore)

## Visibilità giocatore
- Solo con **evento attivo** (`started_at` valorizzato e `ended_at` nullo).
- Tutte le task dell'evento **non esclusive**, più le **esclusive della propria KORP**.

## Premio avvio evento
- Oltre a PC e Crediti base: **`prestigio_base_inizio_evento`** (Integer, può essere negativo).
