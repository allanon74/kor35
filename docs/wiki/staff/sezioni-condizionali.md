# Tessiture e infusioni condizionali

Guida per master e staff. La pagina è visibile **solo allo staff** (sezione **Operatività tecnica**).

Una **sezione condizionale** è un blocco extra (testo e/o numeri di formula) che si accende solo in certi casi. Non serve un’altra tessitura o un’altra infusione: si tiene la tecnica base e si aggiungono le varianti.

Due famiglie:

| Tecnica | Come si attiva la sezione | Cosa può cambiare |
|---------|---------------------------|-------------------|
| **Infusione** | Solo in automatico: il personaggio (o l’oggetto forgiato) soddisfa i requisiti | Testo, statistiche della formula, modificatori al PG o solo all’oggetto |
| **Tessitura** | Automatico (requisiti del PG) **oppure** facoltativo (il giocatore accende un flag con etichetta libera) | Testo e statistiche della formula. I flag si possono combinare |

I requisiti automatici sono gli stessi degli altri editor staff (manifesti, accessi): aura, statistica, caratteristica, abilità, Korp, carriera, carica. Non sono limitati a una sola aura.

---

## 1. Dove si edita

Dashboard staff → tool **Tessiture** oppure **Infusioni** → apri o crea la tecnica → blocco **Sezioni condizionali** (in fondo all’editor).

| Pulsante | Cosa fa |
|----------|---------|
| **+ Sezione** | Aggiunge una sezione automatica (requisiti del personaggio). Sulle tessiture puoi poi passare a **Facoltativa** con il selettore. |
| **+ Facoltativa** | Solo tessiture: crea subito una sezione a flag giocatore. L’**etichetta** la scrivi tu (nome libero del chip). |

Salva la tecnica come sempre. Le sezioni viaggiano con il catalogo (sync master ↔ replica).

---

## 2. Infusioni condizionali

Ogni sezione di un’infusione è **automatica**. Non ci sono flag da accendere a mano.

Campi della sezione:

| Campo | Uso |
|-------|-----|
| **Attiva se** | Gruppo di requisiti AND/OR. Vuoto = sempre attiva. |
| **Testo addizionale** | Compare sotto il testo base solo se la condizione è vera. |
| **Statistiche base** | Valori extra della formula (es. +2 `dannigen`) sommati a quelli dell’infusione. |
| **Modificatori generali** | Bonus al personaggio o solo alle formule dell’oggetto (`ADD` oppure `MOL`). Spunta **Solo formule dell’oggetto** se non deve cambiare le statistiche del PG. |

Alla **forgiatura** le sezioni si copiano sull’oggetto. Da quel momento l’oggetto ha la sua copia: cambiare il catalogo non modifica gli oggetti già creati.

### Catalogo vs scheda

- **Catalogo / anteprima staff** (nessun personaggio): ogni sezione compare in un riquadro «Se …» con l’etichetta della condizione (es. *Se Aura Magica > 1*).
- **Scheda del PG / oggetto in mano**: restano solo le sezioni i cui requisiti sono soddisfatti; l’etichetta «Se …» sparisce e il testo/i numeri si fondono con la tecnica.

### Esempio — infusione che cresce con l’aura

Infusione base: danno 1 fuoco.

1. **+ Sezione**.
2. **Attiva se**: tipo *Aura / punteggio*, nome *Aura Magica*, operatore `>`, soglia `1`.
3. Testo: «L’infusione brucia più forte se l’aura magica è alta.»
4. Statistiche base: `dannigen` = 2.
5. Salva.

Chi ha Aura Magica a 0 o 1 vede solo il danno base. Chi ha 2 o più vede il testo extra e il danno aumentato. Lo stesso vale sull’oggetto forgiato, valutato sul possessore.

---

## 3. Tessiture condizionali

Sulla tessitura ogni sezione ha una **modalità**.

| Modalità | Quando scatta | Cosa vede il giocatore |
|----------|---------------|------------------------|
| **Automatica (requisiti PG)** | Il personaggio soddisfa **Attiva se** | Sulla scheda i numeri si **fondono nella formula principale**. Nel catalogo resta un riquadro «Se Aura Magica > 1» con la formula variante. |
| **Facoltativa (flag giocatore)** | Il giocatore preme il chip (nome = etichetta che hai scritto). Eventuale prerequisito automatico opzionale | La formula base **non cambia**. Sotto compaiono tutte le varianti (*Se A*, *Se B*, *Se A e B*). I chip filtrano quale variante mostrare. |

### Campi extra delle tessiture

| Campo | Uso |
|-------|-----|
| **Etichetta flag** | Solo sezioni facoltative. Nome libero del chip (scelto dallo staff). Diventa anche il flag nelle formule `{if}`: slug in minuscolo senza spazi. |
| **Prerequisito automatico (opzionale)** | Sulle sezioni facoltative: il chip compare solo se il PG soddisfa anche questo (es. un’abilità). Lascia i requisiti vuoti se chiunque può accendere il flag. |
| **Sostituisci il bersaglio** | Azzera i parametri di bersaglio della formula base (`tocco`, `dardo`, `flusso`, `cono`, `esplos`, `tutti`) e applica quelli della sezione. Serve per passare da tocco a esplosione senza sommare i due. |

Le tessiture **non** hanno modificatori generali di sezione (quelli restano sulle infusioni).

### Combinazioni

Con 2 flag il sistema mostra 3 varianti (A, B, A+B). Con 3 flag mostra tutte le combinazioni. Oltre 3 flag mostra solo le varianti singole, senza il prodotto cartesiano.

Sulla scheda, **Condizioni facoltative**:

- nessun chip acceso → tutte le varianti visibili;
- uno o più chip → solo la variante che corrisponde esattamente a quella selezione.

---

## 4. Ricetta da copiare — danno base + flag danno + flag area

Tecnica: tessitura di attacco. Le etichette dei flag le scegli tu; qui usiamo `Intensifica` e `Ampia` solo come nomi di esempio.

### Formula base

Nella formula della tessitura (builder o campo formula):

- danno: statistica `dannigen` = **1**;
- bersaglio: **Tocco** (o quello che usi di default).

Testo libero della tessitura: la descrizione sempre visibile.

### Sezione 1 — automatica (opzionale)

Solo se vuoi che l’aura alzi il danno da sola, senza flag.

1. **+ Sezione**, modalità **Automatica**.
2. **Attiva se**: *Aura / punteggio* → *Aura Magica* `>` `1` (o un’altra aura).
3. Statistiche base: `dannigen` = 2 (si **somma** al 1 della base → 3 sulla scheda di chi ha l’aura).
4. Testo addizionale: «Potenziata dall’aura magica.»

Senza personaggio (catalogo) compare il riquadro *Se Aura Magica > 1*. Sulla scheda di chi non ha l’aura il riquadro non c’è e la formula resta a 1.

### Sezione 2 — facoltativa (più danno)

1. **+ Facoltativa** (o **+ Sezione** → **Facoltativa**).
2. Etichetta libera, es. `Intensifica`.
3. Requisiti vuoti, se tutti possono usarla.
4. Statistiche base: `dannigen` = **4** (si somma: 1+4 = 5, oppure 3+4 se l’aura automatica è già attiva).
5. *Sostituisci il bersaglio* spento.
6. Testo: descrizione dell’effetto quando il flag è attivo.

Nella formula puoi anche scrivere `{if intensifica}…{endif}`: il blocco compare solo nelle varianti che includono quel flag.

### Sezione 3 — facoltativa (cambia bersaglio)

1. **+ Facoltativa**.
2. Etichetta libera, es. `Ampia`.
3. Requisiti vuoti.
4. Accendi **Sostituisci il bersaglio**.
5. Statistiche base: `esplos` = **1**. Se l’esplosione di default (5 m) non basta, aggiungi anche il parametro di area usato in catalogo (es. `area` = 5) come statistica della sezione.
6. Testo: descrizione dell’effetto ad area.

*Sostituisci il bersaglio* toglie il tocco della base e mette l’esplosione. Senza quella spunta tocco ed esplosione resterebbero entrambi.

### Cosa deve vedere lo staff dopo il salvataggio

Nel catalogo (nessun PG):

- formula base: 1 danno, tocco;
- riquadro automatico *Se Aura Magica > 1* (se l’hai creata);
- *Se Intensifica*, *Se Ampia*, *Se Intensifica e Ampia* (con i nomi che hai scelto).

Sulla scheda di un PG con Aura Magica alta:

- formula principale già a 3 (1+2);
- chip con le tue etichette;
- varianti aggiornate quando attiva uno o entrambi i chip.

---

## 5. Tipi di requisito

Nel gruppo **Attiva se** / **Prerequisito automatico**:

| Tipo | Esempio |
|------|---------|
| **Aura / punteggio** | Aura Magica `>` 1, Aura Arcana `≥` 2 |
| **Statistica (sigla)** | `FOR` `≥` 3 |
| **Caratteristica** | una caratteristica del catalogo con soglia |
| **Abilità** | il PG possiede quell’abilità |
| **KORP / Carriera / Carica** | appartenenza |

Operatore del gruppo: **AND** (tutti) o **OR** (almeno uno). Operatori numerici: `>`, `≥`, `<`, `≤`, `=`.

Senza requisiti la sezione automatica è sempre considerata attiva (nel catalogo compare *Sempre attiva*). Sulle sezioni facoltative, requisiti vuoti = il flag è sempre disponibile.

---

## 6. Formule `{if}` e flag

L’etichetta della sezione facoltativa diventa un flag in minuscolo, senza spazi (`Rito solare` → `rito_solare`).

Nella formula o nel testo puoi scrivere:

```text
{dannigen|:N}{if intensifica} (potenziato){endif}{if ampia} ad area{endif}
```

Il pezzo tra `{if …}` e `{endif}` compare solo se quel flag è acceso in quella variante. I chip del giocatore e le combinazioni usano lo stesso meccanismo.

Non usare `{if}` da solo per nascondere un effetto se puoi metterlo in una sezione: la sezione tiene insieme testo, numeri e bersaglio.

---

## 7. Controllo rapido dopo il salvataggio

1. Apri la tecnica dal catalogo staff (senza personaggio): vedi i riquadri «Se …» e, sulle tessiture, tutte le combinazioni dei flag.
2. Apri la stessa tecnica dalla scheda di un PG che **non** soddisfa i requisiti automatici: i riquadri auto non ci sono; i chip facoltativi restano (se non hanno un prerequisito extra).
3. Apri la scheda di un PG che **soddisfa** i requisiti: la formula principale è già aggiornata (tessitura) oppure il testo/modificatore extra è visibile (infusione).
4. Tessitura: premi i chip uno alla volta e insieme; deve restare visibile solo la variante corrispondente.
5. Infusione: forgia un oggetto di prova; le sezioni devono essere sull’oggetto. Cambia il catalogo e verifica che l’oggetto già forgiato non cambi.
6. Replica / evento: dopo il sync la tecnica e le sezioni devono coincidere sul nodo edge (stesso `sync_id`).
