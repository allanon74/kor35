# Mercato scambio carte (staff)

> Pagina **solo master**. Stato implementazione e regole operative.

## Obiettivo

Permettere ai personaggi della **stessa campagna** di scambiarsi copie di carte collezionabili (o crediti) senza passare dallo staff.

## Modello dati (MVP)

`OffertaScambioCarte` (admin Django → gruppo **Carte**):

| Campo | Descrizione |
|-------|-------------|
| `offerente` | PG che propone lo scambio |
| `carta_offerta` | Istanza `CartaPosseduta` offerta |
| `richiesta_carta` | Carta catalogo desiderata (opzionale) |
| `richiesta_crediti` | Crediti richiesti (opzionale) |
| `stato` | `APR` aperta, `ACC` accettata, `ANN` annullata, `SCD` scaduta |
| `accettante` | PG che accetta (quando `ACC`) |

Almeno uno tra `richiesta_carta` e `richiesta_crediti` dovrebbe essere valorizzato per un’offerta sensata.

## Regole previste (API/UI — in sviluppo)

1. Solo PG con accesso carte attivo nella campagna.
2. La carta offerta non deve essere equipaggiata nel reliquiario né in un mazzo duello attivo.
3. L’accettante deve possedere una copia della carta richiesta (se specificata) o sufficienti crediti.
4. Lo scambio è atomico: trasferimento proprietà `CartaPosseduta` + eventuale movimento crediti in `transaction.atomic()`.
5. Record sincronizzabile (`sync_id`, `updated_at`) per edge sync.

## Dove gestire oggi

- **App giocatore** → tab **Mercato** in Cronache delle Sette Elegie.
- **Dashboard staff** → Carte collezionabili → tab **Mercato scambi** (riepilogo e storico).
- **Admin Django** → `[Carte] Offerte scambio carte` per interventi manuali.

## API

| Metodo | URL | Descrizione |
|--------|-----|-------------|
| GET | `/api/carte/mercato/?char_id=` | Offerte aperte, mie offerte, storico |
| POST | `/api/carte/mercato/` | Crea offerta |
| POST | `/api/carte/mercato/accetta/` | Accetta offerta |
| POST | `/api/carte/mercato/annulla/` | Annulla (solo offerente) |
| GET | `/api/staff/carte/scambi/` | Riepilogo staff (`?stato=ACC`) |

## Prossimi passi (opzionali)

---

*Sorgente: `docs/wiki/carte/mercato-scambio.md` — slug `carte-mercato-scambio`.*
