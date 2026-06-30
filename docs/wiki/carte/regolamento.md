# Regolamento carte — bozza MVP

> Documento di lavoro. Aggiorna questa pagina dalla Wiki o riesegui la sincronizzazione da staff.

## Obiettivo del gioco

**Cronache delle Sette Elegie** è un gioco di carte collezionabili legato al mondo KOR35. I personaggi ottengono carte da bustine, le equipaggiano nel **Reliquiario** per bonus passivi e possono sfidarsi in **duelli live**.

## Struttura collezione

- **Espansioni**: insiemi tematici di carte (ogni espansione ha le proprie bustine).
- **Bustine**: pacchetti acquistabili con crediti in-game o tramite QR evento.
- **Rarità**: Comune → Non comune → Rara → Epica → Leggendaria → Unica.

## Mazzo da duello

- **15 carte** esattamente.
- Almeno **2 energie diverse** nel mazzo.
- Almeno **2 carte Naturali** (Marziale, Tecnologica, Innata) e **2 Soprannaturali**.
- Massimo **6 carte** per singola energia.
- Carte **Uniche**: 1 copia; altre carte al massimo **2 copie** se `duplicabile`.

## Duello live (MVP)

- **Influenza** iniziale: 20 per giocatore. Vince chi porta l'influenza avversaria a 0.
- Turni alternati; azioni: gioca carta, attacca, passa.
- Sincronizzazione in tempo reale via app.

### Avvio partita

| Modalità gioco | Come si inizia una partita |
|----------------|----------------------------|
| **TEST** | Sfida a distanza: scegli l'avversario da una lista (tab Carte). Puoi accettare anche con codice invito. |
| **OPEN** (produzione) | **Apri scontro** (tab Carte) → mostra il **QR della sessione** → l'avversario lo scansiona e **si unisce** → fase **pre-partita** (mazzo, posta, pronto) → partita. |

In OPEN la posta può essere 0 o in CR (riserva scommesse o crediti). Modalità **live** (turni in app) o **manuale** (tavolo fisico).

## Reliquiario

- **5 slot** equipaggiabili.
- Bonus passivi da `bonus_equip` sulle carte (es. +1 a una statistica).
- Combo **legami** se equipaggi carte collegate (stesso `legame_id`, set, energie).

## Keyword

Nel testo delle carte le **parole chiave** hanno significato regolamentare. Sono evidenziate in grassetto; se c'è spazio compare un promemoria breve tra parentesi, altrimenti tocca la parola per il testo completo.

Le keyword si definiscono in **staff → Carte → Keywords** (i master hanno anche la guida Wiki *Keyword carte — guida master*, solo staff). Supportano **parametri** con placeholder `[X]`, `[Y]`, … nel nome e nel testo regola.

### Esempio parametrizzato: Mutazione

| Campo staff | Valore |
|-------------|--------|
| Nome | `Mutazione [X]` |
| Testo regola | `Quando questo personaggio si esaurisce, sostituiscilo con una carta fino a costo [X].` |

Su una carta che contiene **Mutazione 0**, il giocatore vede la regola con *costo 0*.

### Esempi fissi (bozza)

| Keyword | Significato (bozza) |
|---------|---------------------|
| Evocazione | Metti in gioco una carta dalla mano pagando il costo energia. |
| Influenza | Punti «vita» del duello (partenza 20). |

Sync sorgenti Wiki: `make wiki-carte-sync ENV=dev-home` — vedi `docs/wiki/carte/README.md`.

## Economia bustine

- Limite giornaliero e **pity** (bustine senza Rara+): configurabili da staff per campagna.
- Il pool di una bustina è limitato all'**espansione** collegata.

---

*Ultimo aggiornamento: bozza iniziale generata dal repository.*
