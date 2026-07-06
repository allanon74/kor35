# Keyword carte — guida master / staff

> **Pagina solo staff** (master, head master, admin). I giocatori non la vedono in Wiki.
> Per le regole di gioco rivolte ai PG usa [Regolamento carte (bozza)](carte-collezionabili-regolamento).

## A cosa servono

Le **keyword** collegano il testo stampato sulle carte a regole leggibili in app: evidenziazione, promemoria breve, testo completo al tap. Oggi sono **regolamento + UX**; il **motore automatico** in duello (attacco, mana, sostituzioni, ecc.) si costruirà sopra gli stessi concetti tramite script JSON (vedi [Roadmap motore effetti](#roadmap-motore-effetti-bozza)).

## Dove si gestiscono

| Dove | Cosa |
|------|------|
| **Dashboard staff → Carte collezionabili → tab Keywords** | Creazione, modifica, disattivazione |
| **Wiki → Gioco carte → questa pagina** | Manuale operativo (sorgente repo) |
| **Wiki → Gioco carte → Regolamento** | Bozza regole per i giocatori (quando OPEN) |

Le keyword sono **per campagna** (`sync_id` / edge sync): su mirror/replica conviene editarle sul master o fare pull dopo le modifiche.

## Campi del form staff

| Campo | Obbligatorio | Descrizione |
|-------|--------------|-------------|
| **Codice** | Sì | Identificatore univoco per campagna, maiuscolo, es. `MUTAZIONE`. Usato anche come termine di match se diverso dal nome. |
| **Nome** | Sì | Testo cercato nel `testo_gioco` della carta. Può contenere placeholder `[X]`, `[Y]`, … |
| **Testo regola** | Sì | Regola completa mostrata al giocatore (tooltip). Stessi placeholder del nome, con valori sostituiti dal match. |
| **Reminder breve** | No | Testo tra parentesi dopo la keyword **solo se** c’è spazio sulla riga (~90 caratteri). Stessi placeholder. |
| **Priorità** | No (default 0) | Intero: **più alto = preferito** se due keyword si sovrappongono sulla stessa posizione del testo. |
| **Attiva** | Sì | Disattivare senza cancellare (es. playtest). |
| **Effect script** | No | JSON **EffectScript v1** per automazione duello; vedi [EffectScript v1](carte-effect-script-v1). |

### Validazione automatica

Se il **nome** contiene `[X]` (o `[Y]`, …), il **testo regola** deve includere **gli stessi placeholder** letterali, es. `…costo [X].` — altrimenti il salvataggio API restituisce errore.

## Placeholder parametrizzati

| Regola | Esempio |
|--------|---------|
| Sintassi | `[X]`, `[Y]`, `[Z]` — solo **lettere maiuscole** |
| Nel nome | `Mutazione [X]` |
| Nel testo carta | `… Mutazione 0 …` oppure `… Mutazione 3 …` |
| Valore catturato | Numero intero (con segno) o parola senza spazi |
| Sostituzione | Nel testo regola e nel reminder, `[X]` → valore letto dalla carta (`0`, `3`, …) |

Spazi flessibili: `Mutazione  0` e `Mutazione 0` sono equivalenti nel match del nome template.

### Esempio completo: Mutazione

| Campo | Valore |
|-------|--------|
| Codice | `MUTAZIONE` |
| Nome | `Mutazione [X]` |
| Testo regola | `Quando questo personaggio si esaurisce, sostituiscilo con un Personaggio dalla mano con costo gioco ≤ [X].` |
| Reminder breve | `sostituisci fino a costo [X]` |
| Priorità | `10` |

Su carta con testo: `Alla morte: Mutazione 0 sul campo.` → l’app evidenzia **Mutazione 0**; al tap la regola mostra *costo ≤ 0*.

### Esempio keyword fissa

| Campo | Valore |
|-------|--------|
| Codice | `EVOCAZIONE` |
| Nome | `Evocazione` |
| Testo regola | `Gioca questa carta dalla mano pagando il costo energia indicato.` |
| Reminder breve | `paga energia e metti in gioco` |

Nessun placeholder: il nome deve comparire **identico** (case insensitive) nel testo carta.

## Come scrivere il testo sulle carte (catalogo)

1. Usa il **nome keyword** (o la forma parametrizzata) nel campo **Testo gioco** della carta in staff → Catalogo.
2. Per keyword parametrizzate scrivi il valore subito dopo il nome: `Mutazione 2`, non `Mutazione (2)`.
3. Evita sottostringhe ambigue: se hai `Mutazione` e `Mutazione rapida`, alza la **priorità** della più specifica.
4. Il **codice** può fare da alias di match (utile se il nome display è lungo).

## Comportamento in app (giocatore)

1. All’apertura collezione/duello, il backend invia l’elenco keyword della campagna.
2. `CardRulesText` tokenizza il `testo_gioco` e applica i matcher (esatto + template).
3. Keyword trovata → **grassetto**; se c’è spazio → *reminder* in corsivo; altrimenti **tap** → tooltip con testo regola (placeholder già risolti).

**Nota:** il duello live esegue gli **EffectScript** collegati alle keyword (vedi Wiki EffectScript v1). Le keyword senza script restano guida testuale + evidenziazione.

## Priorità e conflitti

Ordine di scansione del testo: da sinistra a destra, alla stessa posizione vince la keyword con **priorità più alta**; a parità, ordine alfabetico del termine.

Consiglio operativo:

- Keyword generiche → priorità bassa (0–5)
- Keyword con parametri o nome lungo → priorità media (10–20)
- Eccezioni molto specifiche → priorità alta (30+)

## Configurazione gioco e visibilità Wiki

| `accesso_modo` (Config carte) | Chi gioca | Chi vede regolamento Wiki PG |
|-------------------------------|-----------|------------------------------|
| `OFF` | Nessuno | Solo staff |
| `TEST` | Solo PNG staff (`tipologia.giocante = false`) | Solo staff |
| `OPEN` | Tutti i PG | Tutti i PG + staff |

**Questa pagina** resta sempre **solo master+** indipendentemente dalla modalità.

Sync Wiki da repo:

```bash
make wiki-carte-sync ENV=dev-home WIKI_CARTE_FORCE=1
```

Oppure: **Carte collezionabili → Config → Sincronizza da repo**.

Dopo edit di questo markdown, rieseguire il sync con `--force` / `WIKI_CARTE_FORCE=1` per sovrascrivere la Wiki DB.

## Duello — cosa deve sapere il master (stato attuale)

| Modalità | Avvio partita |
|----------|----------------|
| **TEST** | Lista avversari + codice invito (tab Carte) |
| **OPEN** | **Apri scontro** → QR sessione → avversario **Unisciti** (scanner) → **pre-partita** (mazzo, posta, pronto) |

Pre-partita OPEN:

- **Posta** in CR (anche 0): il creatore propone, l’altro accetta o contropropone.
- Fonte posta: **riserva scommesse** o **crediti** (scelta per giocatore).
- A fine partita con posta: perdente paga dalla fonte scelta; vincitore incassa sui **crediti** personali.
- **Modalità partita:** turni live (app) o **manuale** (tavolo fisico, ± influenza in app).

## Roadmap motore effetti (bozza)

Vedi pagina Wiki dedicata **[EffectScript v1 — vocabolario](carte-effect-script-v1)** (solo staff) per il riferimento completo.

Obiettivo: ogni keyword può avere un campo **`effect_script`** (JSON v1) interpretato dal server in duello — stessi parametri `[X]` del nome.

Esempio logico per **Mutazione [X]** (non ancora implementato):

```json
{
  "trigger": { "event": "unit_exhausted", "source": "this" },
  "steps": [
    {
      "type": "player_choice",
      "id": "replacement",
      "filter": {
        "zone": "hand",
        "card_type": "personaggio",
        "cost_lte": { "ref": "param.X" }
      }
    },
    { "type": "replace", "slot": "this", "with": { "ref": "choice.replacement" } }
  ]
}
```

Primitive pianificate: `PLAY_CARD`, `SPEND_ENERGY`, `DEAL_DAMAGE`, `REPLACE`, `CHOOSE`, trigger `on_play` / `on_exhaust` / `on_attack`.

Il **compositore staff** (form → JSON) arriverà dopo il vocabolario stabile. Fino ad allora: keyword testuali + modalità manuale in OPEN.

## Checklist master prima di un evento carte

- [ ] `accesso_modo` corretto (TEST in prova, OPEN in produzione)
- [ ] Keyword attive e testate su 2–3 carte campione nel catalogo
- [ ] Regolamento Wiki sincronizzato (`make wiki-carte-sync … FORCE=1`)
- [ ] Bustine/espansioni attive e QR bustina verificati se in campo
- [ ] PG con mazzo da 15 carte valido (min 8 PG, max 2 terre, max 3 aure, affinità OGG/EVT)
- [ ] Per OPEN: spiegare flusso **Apri scontro** / QR / pre-partita

## Lavori in coda (sviluppo)

| # | Voce | Stato |
|---|------|--------|
| 1 | Notifica push `DUELLO_LOBBY` | ✅ |
| 2 | UI manuale più ricca (campo, luogo, energia) | ✅ |
| 3 | Regolamento PG allineato lobby OPEN | ✅ repo (sync Wiki) |
| 4 | **EffectScript v1** — schema, validazione, campo keyword, motore MVP | ✅ |
| 5 | Trigger automatico `on_exhaust` da testo carta in duello | ✅ |
| 6 | Compositore visuale staff (form → JSON) | ✅ Mutazione, Colpo, Pesca, Rigenerazione, Ferita |
| 7 | Automazione completa attacco / mana / luoghi | ✅ MVP |
| 8 | Notifica `DUELLO_INIZIO` | ✅ |
| 9 | QR personaggio → lobby OPEN (no sfida diretta) | ✅ |
| 10 | UI campo live (luogo, oggetti, mazzo) | ✅ |

### Prossima fase (idee)

- ~~Effetti a catena multipli sullo stesso evento~~ ✅ (coda FIFO `effect_queue`)
- ~~Scelta bersaglio da `player_choice` (non solo carte)~~ ✅ (`filter.target: hero`)
- ~~Compositori: Rigenerazione energia, Danno diretto eroe~~ ✅
- ~~Sync wiki prod dopo ogni release carte~~ ✅ (`deploy.yml` → `sync_wiki_carte_regolamento --force`)

---

*Sorgente: `docs/wiki/carte/keywords-staff.md` — pagina Wiki slug `carte-keywords-staff`.*
