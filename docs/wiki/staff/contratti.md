# Contratti — impostare modelli e slot

Guida per lo staff. La pagina è visibile solo allo staff (sezione **Operatività tecnica**).

I sei nomi Talento, Creatore, Pubblicitario, Protettore, Mercenario e Agente sono **esempi già previsti**. L’editor non è una maschera diversa per ciascuno: è sempre la stessa, e un contratto nuovo si ottiene combinando gli effetti elencati sotto.

Un personaggio appartiene a **una sola Korp**.

Finché il modulo campagna `contratti` è `OFF`, i giocatori non vedono la tab e lo staff non usa ancora l’editor. Questa pagina è la procedura da seguire quando il modulo è `TEST` o `OPEN`.

---

## 1. Accendere il modulo

Nella campagna, moduli di accesso, chiave **contratti**:

| Modo | Chi lo vede |
|------|-------------|
| `OFF` | Nessuno. Nessun bonus viene erogato. È lo stato iniziale. |
| `TEST` | Solo staff e master. Utile per provare un modello senza aprirlo ai giocatori. |
| `OPEN` | I personaggi della Korp che sottoscrive, più chi ha già un contratto firmato o una proposta da firmare. |

In `TEST` conviene creare i modelli e firmare con due personaggi staff prima di passare a `OPEN`.

---

## 2. Slot di contratto, per Korp e per carica

Lo **slot** è quante proposte o contratti il personaggio può tenere aperti **come proponente**. Il cliente non consuma slot.

Formula, ricalcolata ogni volta (non si scrive un numero fisso sulla scheda):

```text
slot = base della Korp
     + bonus della carica
     + statistica SCT
```

| Dove | Campo | Cosa ci metti |
|------|--------|----------------|
| Korp | `sottoscrive_contratti` | Se spento, quella Korp non offre contratti e i suoi membri hanno 0 slot. |
| Korp | `slot_contratto_base` | Intero libero, **diverso per ogni Korp**. Il 3 è solo il valore suggerito all’inizio, non un obbligo. |
| Carica | `bonus_slot_contratto` | Intero libero, **diverso per ogni carica**. Il valore iniziale è 0: il grado d’ingresso non aggiunge slot da solo. Può essere +1, +2, oppure negativo. |
| Scheda / abilità | statistica **SCT** | Creata dalla migrazione, parametro `SCT`, valore di partenza 0. Un’abilità di default della Korp, un’abilità acquistata o un oggetto la aumentano. Conta solo se la Korp sottoscrive. |

Senza carica il bonus carica è 0. Occupano uno slot le proposte in attesa e i contratti stipulati. Rifiuto, annullamento, scadenza e scioglimento liberano lo slot.

### Esempio — tre Korp, cariche diverse

**Vigilanza** sottoscrive, base **3**.

| Carica | Bonus | Slot di un membro con SCT a 0 |
|--------|------:|-------------------------------:|
| Recluta | 0 | 3 |
| Capitano | +1 | 4 |
| Comandante | +2 | 5 |

Un Comandante con un’abilità che dà SCT +1 ha **6** slot.

**Archivio** sottoscrive, base **1**. Tutte le cariche hanno bonus 0. Ogni membro ha **1** slot, qualunque sia il grado. Un’abilità SCT +1 lo porta a 2.

**Mercanti** non sottoscrive. Base e cariche non contano: **0** slot, niente tab per proporre, niente modelli offrili. Se un Mercante firma come cliente il contratto di un Vigilanza, la tab gli compare solo per leggere e gestire quel contratto.

---

## 3. Come è fatto un modello

Dashboard staff → tool **Contratti** → nuovo modello. I campi sono sempre questi, per qualunque contratto futuro.

| Pezzo | A cosa serve |
|-------|----------------|
| Korp | Solo i membri di quella Korp possono proporlo. |
| Nome | È l’etichetta che vede il giocatore. Non esiste un tipo fisso separato dal nome. |
| Chiave di esclusività | Testo libero, opzionale. Il cliente può avere **un solo** contratto stipulato per la stessa chiave. Vuota = può firmarne quanti vuole di quel modello, gli slot del proponente permettendo. |
| Durata | `GIORNI` = N giorni reali da quando nasce la proposta. `FINE_EVENTO` = scade alla `data_fine` dell’evento scelto in proposta. La data mostrata in firma non si sposta. |
| Testo | Ciò che il cliente legge sul QR. Segnaposto: `{{proponente}}`, `{{cliente}}`, `{{korp}}`, `{{scadenza}}`, `{{parametri}}`, `{{clausole}}`, `{{compensi}}`. |
| Parametri | Righe che aggiungi tu. Vedi sotto. |
| Effetti | Comportamenti di gioco, presi dall’elenco. Il numero può essere fisso o legato a un parametro. |
| Clausole | Testo che il proponente può aggiungere. Possono portare effetti extra, attivi solo se scelte. |
| Compensi | Stessa cosa delle clausole, presentata al giocatore come compenso. Di solito un effetto `credito_creato` o `trasferimento`. |

Alla proposta il sistema **fotografa** parametri, effetti e testo. Se dopo cambi il modello, i contratti già emessi restano com’erano.

### Parametri: come aggiungerne uno

Ogni riga ha:

| Campo | Valori |
|-------|--------|
| Chiave | Nome interno stabile, senza spazi. Esempio: `pct_cliente`, `tema`, `somma`. |
| Etichetta | Frase che legge il proponente. |
| Tipo | `INTERO`, `DECIMALE`, `PERCENTUALE`, `TESTO`, `SCELTA`, `PERSONAGGIO`. |
| Chi compila | `STAFF` = valore fisso sul modello. `PROPONENTE` = lo sceglie quando crea la proposta, dentro min e max. |
| Min, max, default | Per i numeri. Per `SCELTA`, l’elenco delle voci. `PERSONAGGIO` serve a indicare un erede. |

Dentro un effetto, un importo si scrive come numero secco oppure come `{{param:chiave}}`.

**Esempio.** Vuoi un Talento in cui lo staff blocca il 10% al cliente e il proponente sceglie la propria percentuale fra 5 e 25:

1. Parametro `pct_cliente`, tipo percentuale, chi compila STAFF, valore 10.
2. Parametro `pct_proponente`, tipo percentuale, chi compila PROPONENTE, min 5, max 25, default 10.
3. Effetto `percentuale_task` con `pct_cliente = {{param:pct_cliente}}` e `pct_proponente = {{param:pct_proponente}}`.

---

## 4. Dove finiscono i crediti

Tutti i **bonus** (crediti creati dal sistema: percentuale task, bonus del creatore, compenso dell’agente, quota dei post) vanno sul **conto deposito**. Sono guadagni extra, come le ricompense delle task.

I **trasferimenti** tra i due personaggi (prezzo del protettore, paga del mercenario, indennizzo pubblicitario, rimborso, penale) usano lo stesso conto deposito.

Se un trasferimento non è coperto dal saldo:

- **in firma** (`se_scoperto = BLOCCA`): la firma non avviene;
- **dopo** (indennizzo, penale, rimborso, paga a inizio evento): si versa quel che c’è e il resto resta un **debito** visibile allo staff. Il saldo non scende sotto zero. Lo staff salda il debito quando il personaggio ha crediti.

Ogni pagamento nasce una sola volta. Ripetere la chiusura evento o il sync non paga due volte.

---

## 5. Gli effetti, uno per uno

Si aggiungono con **Aggiungi effetto**. L’ordine delle righe è solo di lettura. La tab del giocatore mostra «associa post», «registra servizio», «segnala ferita» o «attiva» soltanto se l’effetto corrispondente è nel contratto.

### `credito_creato`

Crea crediti nuovi sul deposito.

| Campo | Significato |
|-------|-------------|
| Innesco | `ALLA_STIPULA`, `A_INIZIO_EVENTO`, `A_FINE_EVENTO`, `A_SCADENZA`, `AD_ATTIVAZIONE`, `MANUALE` |
| Beneficiario | `CLIENTE`, `PROPONENTE` o `ENTRAMBI` |
| Importo | Numero, o `{{param:…}}` |

`MANUALE` resta un pulsante staff. `AD_ATTIVAZIONE` parte solo quando scatta l’effetto `attivazione`.

### `trasferimento`

Sposta crediti da un contraente all’altro. Non li crea.

| Campo | Significato |
|-------|-------------|
| Innesco | Come `credito_creato` |
| Da / A | `CLIENTE` o `PROPONENTE` |
| Importo | Numero o parametro |
| Se scoperto | `BLOCCA` solo se l’innesco è la firma. Altrimenti `DEBITO` |

### `percentuale_task`

Quando il **cliente** reclama i crediti di una task, sulla cifra già accreditata (dopo il fattore Korp della task):

- il cliente riceve un ulteriore `cifra × pct_cliente / 100`;
- il proponente riceve `cifra × pct_proponente / 100`.

Il prestigio della task non entra. Le task completate dal proponente non attivano questo effetto.

| Campo | Esempio Talento classico |
|-------|--------------------------|
| `pct_cliente` | 10 |
| `pct_proponente` | 20 |

Task da 100 crediti: il cliente aveva già preso 100, ne riceve altri **10** (totale 110). Il proponente riceve **20**. Entrambi sul deposito.

### `sconto_costo`

Quando il cliente paga un costo negli ambiti spuntati. La base è il **costo pieno**, prima dello sconto RCT e prima di questo contratto.

| Campo | Significato |
|-------|-------------|
| Ambiti | Uno o più tra `creazione_infusione`, `creazione_cerimoniale`, `creazione_tessitura`, `forgiatura`, `consumabile` |
| `pct_sconto_cliente` | Percentuale tolta dal pagamento del cliente |
| `pct_bonus_proponente` | Percentuale del pieno, accreditata al proponente |

Il cliente paga `max(0, pieno − sconto RCT − pieno × pct_sconto / 100)`. Il bonus del proponente resta calcolato sul pieno anche se il cliente arriva a pagare zero.

**Esempio.** Forgiatura, pieno 600, 10% e 10%, senza RCT. Il cliente paga 540 invece di 600. Il proponente riceve 60 sul deposito. Con RCT al 10% lo sconto RCT è altri 60: il cliente paga 480; il proponente riceve comunque 60.

### `post_tetto_evento`

A **Termina evento**. Il proponente, durante l’evento, associa i propri post social al contratto. Un post vale per un solo contratto che ha questo effetto. Lo staff può scollegarlo. Il testo del post non viene letto in automatico: il tema è un parametro che i due hanno concordato, non una parola chiave.

| Campo | Esempio |
|-------|---------|
| `massimo_post` | 3 |
| `crediti_per_post` | 30 |

Il parametro `tema` (tipo TESTO, compilato dal proponente) non è un campo dell’effetto: va nel testo del contratto, per esempio «parlare di: {{param:tema}}».

Chiusura, con tetto 3 e 30 a post. Il cliente deve sempre arrivare a 90. L’indennizzo dei post mancanti lo versa il proponente.

| Post scritti | Credito creato a ciascuno | Indennizzo proponente → cliente | Netto cliente | Netto proponente |
|-------------:|--------------------------:|--------------------------------:|--------------:|-----------------:|
| 0 | 0 | 90 | 90 | −90 (o debito) |
| 2 | 60 | 30 | 90 | 30 |
| 3 | 90 | 0 | 90 | 90 |
| 5 | 90 | 0 | 90 | 90 |

I post oltre il massimo si scartano. Se il proponente ha solo 10 sul deposito e deve versare 30, versa 10 e resta un debito di 20.

La tab mostra l’anteprima prima della chiusura evento. La chiusura si può ripetere: non paga una seconda volta.

### `contatore_servizi`

Non muove crediti. Conta ore o quest registrate sul contratto, con un tetto per evento.

| Campo | Esempio |
|-------|---------|
| Unità | `ORE` oppure `QUEST` |
| `massimo_per_evento` | 4 |

Il proponente registra la prestazione. Oltre il tetto la registrazione è rifiutata.

### `penale_confermata`

Non scatta da sola.

| Campo | Significato |
|-------|-------------|
| Evento | `FERITA` oppure `MORTE` |
| Da / A | Chi versa e chi riceve |
| Importo | Numero o parametro. Per la ferita del protettore, di solito la stessa somma già versata alla firma |
| Conferma | `CONTROPARTE` (l’altro contraente) oppure `STAFF` |
| A morte paga | `CLIENTE` oppure `EREDE` |

**Ferita.** È un’azione sul contratto («Segnala ferita grave»), non un nuovo stato sulla scheda personaggio. Dopo la conferma parte il trasferimento. Se il saldo non basta, il resto è debito.

**Morte.** Quando il cliente ha `data_morte` e il contratto è ancora stipulato, nasce una voce in attesa. Lo staff la conferma. Non parte al solo salvataggio della data di morte, perché quella data può essere un errore. Se «a morte paga» è `EREDE`, il proponente in proposta ha scelto un personaggio (parametro tipo `PERSONAGGIO`). Se non l’ha scelto, il rimborso resta sul personaggio morto e lo staff lo gira a mano.

### `attivazione`

Azione del proponente, una volta sola.

| Campo | Significato |
|-------|-------------|
| `richiede_staff` | Se sì, parte solo dopo conferma staff |
| `risolvi_contratto` | Se sì, dopo l’attivazione il contratto passa a risolto e libera lo slot |

Sblocca gli effetti (di modello o di clausola) il cui innesco è `AD_ATTIVAZIONE`.

---

## 6. Ricette da copiare

In editor, **Crea da esempio** prepara queste combinazioni. Si possono duplicare e modificare. La chiave di esclusività è quella indicata: un cliente non firma due Talenti insieme, anche se i modelli hanno nomi diversi, finché la chiave è `talento`.

### Talento — chiave `talento`

- Effetto `percentuale_task`, 10 e 20 (oppure parametri, come nella sezione 3).
- Testo tipo: «Per ogni task completata da {{cliente}}, il cliente riceve un bonus del 10% sui crediti della task e {{proponente}} riceve il 20%. Fino al {{scadenza}}.»

Durata tipica: 90 giorni reali.

### Creatore — chiave `creatore`

- Effetto `sconto_costo`.
- Ambiti: quelli che la Korp vuole coprire. Per il caso discusso: forgiatura e consumabile, più le creazioni di infusione, cerimoniale e tessitura se la Korp le include.
- 10% sconto cliente, 10% bonus proponente.
- Testo: citare gli ambiti e le due percentuali, più `{{scadenza}}`.

Controllo: forgiatura da 600 → cliente −60 sul prezzo, proponente +60 sul deposito.

### Pubblicitario — chiave `pubblicitario`

- Parametro `tema`, testo, compilato dal proponente.
- Effetto `post_tetto_evento`, massimo 3, 30 crediti a post.
- Testo: «{{proponente}} pubblica fino a 3 post per evento su: {{param:tema}}. Ogni post vale 30 crediti a testa, fino al tetto. I post mancanti li indennizza il proponente. Fino al {{scadenza}}.»

I numeri della tabella in sezione 5 sono il controllo: 2 post in un evento → cliente 90, proponente 30.

### Protettore — chiave `protettore`

Il cliente compra protezione.

1. Parametro `somma`, decimale. Esempio fisso staff: 200. Oppure il proponente la sceglie tra 100 e 400.
2. Effetto `trasferimento`, innesco `ALLA_STIPULA`, da cliente, a proponente, importo `{{param:somma}}`, se scoperto `BLOCCA`.
3. Effetto `contatore_servizi`, unità `ORE`, massimo 4 per evento. In alternativa `QUEST`, se la Korp conta le quest e non le ore. Si può mettere in una clausola se non tutte le offerte hanno il tetto.
4. Effetto `penale_confermata`, evento `FERITA`, da proponente, a cliente, importo `{{param:somma}}`, conferma `CONTROPARTE`.
5. Effetto `penale_confermata`, evento `MORTE`, da proponente, a cliente, importo 1000 (o un parametro `penale`), conferma `STAFF`, paga `CLIENTE`.

Se il cliente non ha 200 sul deposito, non riesce a firmare. Una ferita confermata gli rende 200. La morte, dopo conferma staff, preleva 1000 dal proponente (o lascia il debito).

### Mercenario — chiave `mercenario`

Il cliente offre i servigi. Paga il **proponente**.

1. Parametro `paga`, per esempio 150.
2. Effetto `trasferimento`, da proponente, a cliente. Innesco a scelta del modello:
   - `ALLA_STIPULA` con `BLOCCA`, se la paga è unica all’ingresso;
   - `A_INIZIO_EVENTO` con `DEBITO`, se la paga è per ogni evento coperto dal contratto.
3. Clausola di impiego: `contatore_servizi`, `ORE` o `QUEST`, tetto per evento (esempio 6 ore).
4. `penale_confermata` ferita: rimborso proponente → cliente, conferma controparte, importo pari alla paga o a una somma scritta in clausola.
5. `penale_confermata` morte: rimborso, conferma staff. Parametro `erede` di tipo `PERSONAGGIO`, chi compila PROPONENTE, non obbligatorio. In effetto, «a morte paga» = `EREDE`. Senza erede il rimborso resta sul personaggio morto.

### Agente — chiave `agente`

1. Due effetti `credito_creato` alla stipula: 40 al cliente e 40 al proponente (oppure `ENTRAMBI` se l’importo è uguale).
2. Effetto `attivazione`, `richiede_staff` a seconda della Korp, `risolvi_contratto` spento se il dormiente deve restare legato fino a scadenza.
3. Clausole accessorie, ciascuna con il proprio testo (condizione di attivazione) e, se prevedono soldi, un `credito_creato` o un `trasferimento` con innesco `AD_ATTIVAZIONE`.

Alla firma entrambi ricevono 40 sul deposito e non succede altro. All’attivazione partono solo le clausole che erano state scelte nella proposta.

### Contratto nuovo, senza codice — «Patrono»

Non è una settima maschera. Si compone così:

- Nome: Patrono. Chiave di esclusività: `patrono` (così non si accumula con un altro Patrono; non blocca un Talento).
- `trasferimento` cliente → proponente alla stipula, somma 100, `BLOCCA`.
- `percentuale_task` con 5% al cliente e 5% al proponente.
- `penale_confermata` morte, conferma staff, importo 500, dal proponente al cliente.

Se un giorno servirà un effetto che non è in elenco (per esempio un bonus quando si vince un duello di carte), quello sì chiede una riga nuova nel registry. Fino ad allora lo staff non aspetta uno sviluppo per inventare un contratto.

Un modello **senza effetti** è un accordo solo testuale: si firma, scade, non muove crediti. I compensi alla stipula, se li aggiungi, sono effetti `credito_creato` o `trasferimento`.

---

## 7. Controllo rapido dopo aver salvato

1. Modulo almeno in `TEST`.
2. Korp con sottoscrive acceso e base slot quella decisa (non dare per scontato il 3).
3. Cariche con il bonus deciso, grado d’ingresso a 0 se non deve aggiungere slot.
4. Personaggio proponente: slot liberi uguali a base + carica + SCT.
5. Proposta di prova, QR, secondo personaggio che firma.
6. Se c’è un prezzo alla firma, togliere i crediti deposito al cliente (o al proponente, nel mercenario) e verificare che la firma si blocchi.
7. Per Talento: reclamare una task da 100 e leggere +10 e +20 sul deposito.
8. Per Pubblicitario: associare 2 post, terminare l’evento, leggere 90 e 30.
9. Modificare il modello dopo la firma e verificare che il contratto già firmato non cambi numeri.
