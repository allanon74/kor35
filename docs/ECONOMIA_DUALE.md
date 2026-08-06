# Economia duale (conto corrente / deposito)

Feature opzionale per campagna: modulo **`conto_deposito`** (OFF / TEST / OPEN) in Staff → Campagne → Moduli.

## Conti

| Conto | Entrate tipiche | Uscite |
|-------|-----------------|--------|
| **Corrente** | Stipendio / premio presenza evento (+ bonus carriera/carica) | Spese al listino; puntate scommesse “da crediti” |
| **Deposito** | Task, nodi, vincite scommesse (ex-riserva), vendite negozio, royalties, staff add generico | Spese beni se categoria ammessa (prezzo = listino / fattore); puntate “da deposito” |

La vecchia **riserva scommesse** è assorbita nel deposito (campo `Personaggio.riserva` legacy azzerato in migrazione).

## Trasferimento per evento

Una volta per evento il giocatore (tab **Economia**) può spostare deposito → corrente fino a:

`frazione_trasferimento_stipendio × stipendio_evento`

Config in Staff → **Economia crediti** (`Campagna.economia_config`).

## Prezzo deposito

Default `fattore_valore_deposito = 0.90` → `prezzo_deposito = prezzo_corrente / 0.90` (potere d’acquisto ridotto).

## Scambi P2P e messaggi

Nei trasferimenti tra giocatori (proposte transazione e crediti allegati ai messaggi) si sceglie il **conto di origine**.
Debit e credit avvengono **sullo stesso conto**: corrente → corrente, deposito → deposito (nessuna conversione).

- `GET /api/personaggi/api/personaggio/me/economia/?char_id=`
- `POST .../economia/trasferisci-deposito/` `{ char_id, importo }`
- `GET .../economia/movimenti/?char_id=&tipo=crediti|pc`
- Staff: `GET/PATCH .../staff/economia-config/`, `GET/POST .../staff/personaggi/<id>/economia/`

Helper: `personaggi/economia_crediti.py`.
