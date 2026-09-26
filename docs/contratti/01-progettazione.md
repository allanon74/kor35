# Contratti — progettazione

Feature opzionale di gioco: un personaggio **proponente** (soggetto attivo) offre un contratto; un **cliente** (soggetto passivo) lo sottoscrive scansionando un QR. Entrambi sono i **contraenti**.

Il documento fissa il modello, gli automatismi e le decisioni già chiuse. Le voci ancora aperte sono in fondo, ciascuna con un default da usare se non arriva una correzione.

## Gate

Stesso meccanismo di tasks, carte e scommesse: chiave `contratti` in `Campagna.moduli_accesso`.

| Modo | Effetto |
|------|---------|
| `OFF` | Tab giocatore e tool staff assenti. Nessun hook economico. Default di registry. |
| `TEST` | Visibile solo a staff/master (ruolo campagna STAFFER+), come gli altri moduli. |
| `OPEN` | Visibile ai personaggi che superano anche il filtro Korp (sotto). |

Registrazione prevista in `personaggi/campagna_moduli.py` (`CAMPAGNA_MODULI_REGISTRY`, `PLAYER_TAB_TO_MODULO`, `STAFF_TOOL_TO_MODULO`) e nei quattro punti della dashboard staff (`contratti`).

## Chi vede la tab

La tab **Contratti** compare se il modulo è accessibile **e** vale almeno una di queste:

- il personaggio ha una membership Korp attiva su una carriera con `sottoscrive_contratti`;
- ha almeno un contratto in stato `IN_ATTESA` (come proponente) o `STIPULATO` / storico recente (come proponente o cliente).

Creare una proposta richiede in più slot liberi (sotto). Un cliente fuori dalle Korp abilitate firma dal QR e poi vede il contratto nella tab, senza poter proporne di nuovi.

## Slot di contratto

Uno **slot di contratto** è la capacità del proponente di tenere aperta una proposta o un contratto stipulato. Il cliente non consuma slot: è limitato a **un contratto stipulato per tipologia** (Talento, Creatore, …), su tutto il personaggio, non per Korp e non per singolo modello.

### Perché statistica + dati su Korp/Carica

La statistica dà alle abilità, agli oggetti e allo staff lo stesso canale già usato per RCT, RCO e gli altri modificatori (`AbilitaStatistica` → `get_valore_statistica`). I «3 in ingresso» e il «+1 per carica» restano dati di Korp e Carica, come oggi `bonus_crediti_evento` e `bonus_peso_influencer`: lo staff li cambia senza fabbricare un'abilità per ogni grado.

Formula effettiva, ricalcolata a ogni lettura (niente valore derivato salvato sul personaggio):

```text
slot = slot_contratto_base della Korp
     + somma dei bonus_slot_contratto delle cariche attive su quella membership
     + get_valore_statistica("SCT")
```

- `Carriera.sottoscrive_contratti` (bool, default falso). Se falso, quella membership vale 0 e i modelli di quella Korp non sono offrili.
- `Carriera.slot_contratto_base` (intero, default 3). Vale solo se la Korp sottoscrive.
- `Carica.bonus_slot_contratto` (intero, default 0). Lo staff mette +1 sui gradi che devono aggiungerlo.
- Statistica **SCT** «Slot di contratto», `is_numero`, valore base 0. È il solo addendo che abilità e oggetti modificano.

Più membership Korp attive che sottoscrivono **si sommano**. SCT si somma solo se esiste almeno una membership abilitata: fuori da quelle Korp la statistica non apre la possibilità di proporre.

Occupano uno slot gli stati `IN_ATTESA` e `STIPULATO`. Rifiuto, scadenza, risoluzione e annullamento lo liberano. Il proponente non firma la propria proposta.

Default sul grado d'ingresso: la base 3 è già il pacchetto di ingresso; il +1 non è automatico su ogni carica, così il grado iniziale non diventa 4 per sbaglio. Se un grado deve contare, `bonus_slot_contratto = 1`.

## Ciclo di vita

Un solo modello runtime, `Contratto`, con stato:

```text
IN_ATTESA → STIPULATO → SCADUTO
    │            │
    ├→ RIFIUTATO └→ RISOLTO   (scioglimento anticipato, staff o regola)
    └→ ANNULLATO              (il proponente ritira la proposta)
```

1. Il proponente sceglie un modello della propria Korp, compila i parametri lasciati a lui, e — se il modello li ammette — una o più clausole accessorie e uno o più compensi accessori.
2. Il sistema congela uno **snapshot** (parametri, testo già renderizzato, scadenza). Le modifiche successive al catalogo non riscrivono i contratti vivi.
3. Nasce un `QrCode` collegato (stesso canale di negozi e scontri carte). Lo scanner esistente (`QrCodeDetailView`) risponde `tipo_modello: contratto`.
4. Il cliente vede il testo e, in fondo, **Sottoscrivi fino al {data}** oppure **Rifiuta**. La data è quella fissata alla creazione della proposta (`adesso + durata`, oppure `data_fine` dell'evento se la durata è «fine evento»). Non si ricalcola al momento della firma.
5. Se la proposta è già oltre la scadenza, il QR non è più firmabile e lo slot si libera.
6. Alla firma si controlla: modulo attivo, cliente diverso dal proponente, cliente senza un altro `STIPULATO` della stessa tipologia, proposta ancora `IN_ATTESA`. Poi partono i compensi con momento `ALLA_STIPULA`.

La scadenza è pigra: ogni lettura e ogni hook che eroga un bonus marca `SCADUTO` se `now > scadenza`. Gli hook economici agiscono solo su `STIPULATO` ancora nel termine. Funziona anche sul nodo edge offline, senza un cron.

## Catalogo (dashboard staff)

Tool staff **Contratti**. Il catalogo è dati, non codice: una tipologia è un motore; un modello è un'offerta concreta della Korp.

### ModelloContratto

| Campo | Ruolo |
|-------|--------|
| `campagna`, `korp` | Offerta di quella Korp, in quella campagna. |
| `nome`, `attivo` | Voce nel wizard del proponente. |
| `tipologia` | Motore: `TALENTO`, `CREATORE`, `PUBBLICITARIO`, `PROTETTORE`, `MERCENARIO`, `AGENTE`, `GENERICO`. |
| `durata_modo` | `GIORNI` (N giorni reali) oppure `FINE_EVENTO` (scadenza = `data_fine` dell'evento scelto in proposta; deve esistere un evento). |
| `durata_giorni` | Usato se `GIORNI`. |
| `testo` | Testo mostrato alla firma, con segnaposto. |
| `permette_clausole`, `permette_compensi` | Abilitano i due elenchi nel wizard. |

Segnaposto nel testo: `{{proponente}}`, `{{cliente}}`, `{{korp}}`, `{{scadenza}}`, `{{parametri}}`, `{{clausole}}`, `{{compensi}}`. In proposta il cliente è ancora «il sottoscrittore». Lo snapshot sostituisce i valori noti e lascia il nome del cliente vuoto finché non firma; alla firma si rigenera solo il nome, non i numeri.

I parametri numerici non sono un JSON libero inventato in UI. Ogni tipologia ha uno **schema in codice** (chiave, etichetta, tipo, min/max). Sul modello lo staff imposta, per ogni chiave:

- valore fisso, oppure intervallo che il proponente sceglie in proposta;
- se la chiave è testo (il tema pubblicitario, il nome dell'erede), la compila il proponente.

`GENERICO` non ha motore: solo testo, clausole e compensi. Serve per contratti futuri prima che esista un automatismo.

### ClausolaAccessoria e CompensoAccessorio

Collegate a un modello (o, se serve riuso, a una Korp e selezionabili dai modelli di quella Korp).

- Clausola: `nome`, `testo`, `obbligatoria`, `selezionabile`. Effetto strutturato opzionale (importo penale, tetto ore, tetto quest, ricompensa di attivazione). Il testo entra nello snapshot; l'effetto lo legge il motore della tipologia.
- Compenso: `nome`, `testo`, `importo`, `beneficiario` (`PROPONENTE`, `CLIENTE`, `ENTRAMBI`), `momento` (`ALLA_STIPULA`, `A_INIZIO_EVENTO`, `A_FINE_EVENTO`, `AD_ATTIVAZIONE`, `A_SCADENZA`, `MANUALE`).

`ALLA_STIPULA`, `A_INIZIO_EVENTO`, `A_FINE_EVENTO` e `A_SCADENZA` sono automatici. `AD_ATTIVAZIONE` scatta con l'azione di attivazione. `MANUALE` resta un pulsante staff.

## Le sei tipologie

Gli importi dei motori sono crediti. Il conto di accredito dei bonus **creati** dal sistema è il **deposito**, come le task (`reclama_ricompensa`). I versamenti tra contraenti sono trasferimenti (addebito su un PG, accredito sull'altro) e usano lo stesso conto.

Ogni erogazione scrive una riga `ContrattoAdempimento` con chiave unica `(contratto, tipo, fonte)`. Il movimento crediti nasce una sola volta; la riga viaggia nel sync edge. Un secondo nodo che rivede la stessa task o lo stesso post non ripaga.

### Talento

Parametri: `pct_cliente`, `pct_proponente` (es. 10 e 20).

Quando il **cliente** reclama la ricompensa di una task (`reclama_ricompensa` in `gestione_plot/missioni_service.py`), sulla cifra crediti effettivamente accreditata (già dopo fattore Korp):

- il cliente riceve un ulteriore `importo * pct_cliente / 100`;
- il proponente riceve `importo * pct_proponente / 100`.

Esempio: task da 100 crediti → cliente +10, proponente +20, oltre i 100 già presi dal cliente. Il prestigio della task non entra nel contratto. Le task completate dal proponente non attivano il suo contratto come cliente.

### Creatore

Parametri: `pct_sconto_cliente`, `pct_bonus_proponente`, e gli ambiti spuntabili `creazione_infusione`, `creazione_cerimoniale`, `creazione_tessitura`, `forgiatura`, `consumabile`.

Base = costo teorico pieno, prima di RCT e prima dello sconto di contratto.

- Il cliente paga `max(0, pieno − sconto RCT − pieno * pct_sconto_cliente / 100)`.
- Il proponente riceve `pieno * pct_bonus_proponente / 100`, anche se gli sconti portano il pagamento a zero.

Esempio: forgiatura con pieno 600 e 10% / 10% → il cliente paga 60 in meno, il proponente riceve 60. Se c'è anche RCT, lo sconto RCT si somma e il pagamento non scende sotto zero; il bonus del proponente resta calcolato sul pieno.

Un'unica funzione `applica_effetto_creatore(cliente, ambito, costo_pieno, fonte_id)` va chiamata nei punti che già addebitano creazione tecnica, forgiatura da infusione e consumabili da tessitura.

### Pubblicitario

Parametri di modello: `massimo_post_per_evento`, `crediti_per_post` (stessa cifra per entrambi; due campi distinti solo se più avanti serviranno importi diversi). In proposta il proponente scrive il **tema** (testo concordato, es. «la salvezza dell'imperatore»).

Il proponente, dall'app, associa un proprio `SocialPost` dell'evento al contratto. Un post conta per un solo contratto pubblicitario. Lo staff può scollegarlo. Non c'è match automatico sul testo: a un evento dal vivo il tema è una frase, non una keyword affidabile.

A **Termina evento**, per ogni contratto ancora valido in quell'intervallo (`data_inizio`/`data_fine` dell'evento dentro la vita del contratto):

```text
n        = min(post associati validi, massimo)
mancanti = massimo − n
importo  = crediti_per_post

cliente    += n * importo          (credito creato)
proponente += n * importo          (credito creato)
se mancanti > 0:
    trasferimento proponente → cliente di mancanti * importo
```

Esempio con massimo 3 e 30 crediti a post:

- 2 post: ciascuno riceve 60 creati; il proponente versa 30 al cliente. Netto cliente 90, netto proponente 30.
- 5 post: ciascuno riceve 90. I post oltre il massimo non contano.
- 0 post: nessun credito creato; il proponente versa 90 al cliente.

La tab mostra l'anteprima dell'evento in corso prima della chiusura. La chiusura è idempotente per `(contratto, evento)`.

Se il saldo del proponente non copre l'indennizzo, il trasferimento è parziale e il resto resta un **debito** sull'adempimento (`dovuto`, `versato`). Lo staff lo salda quando il PG ha crediti; il debito non porta il saldo sotto zero.

### Protettore

Il cliente compra protezione.

- Alla stipula: trasferimento cliente → proponente della `somma` concordata (parametro fisso o scelto nel range del modello). Se il cliente non ha il saldo, la firma è rifiutata.
- Per ogni evento nella durata: tetto di servizi `max_servizi` in unità `ORE` o `QUEST` (clausola o parametro). Il proponente registra le prestazioni; il tetto è solo un contatore, non un pagamento.
- Ferita grave: azione «Segnala ferita grave» (proponente, cliente o staff). La controparte conferma, oppure conferma lo staff. Poi rimborso automatico della somma pattuita (o dell'importo/percentuale scritto in clausola), proponente → cliente, con la stessa regola del debito se il saldo non basta.
- Morte del cliente (`data_morte` valorizzata mentre il contratto è stipulato): nasce un adempimento di penale in stato da confermare. Lo staff conferma e scatta il trasferimento della penale prevista. Non parte da sola al click su `data_morte`, perché quella data si imposta anche per errore.

Non esiste oggi un modello di ferite. La segnalazione vive sul contratto, non sulla scheda personaggio.

### Mercenario

Il cliente offre i propri servigi al proponente. È il simmetrico del protettore, con i versi dei soldi invertiti.

- Compenso: trasferimento proponente → cliente.
- Momento, scelto sul modello: `ALLA_STIPULA` oppure `A_INIZIO_EVENTO` (una volta per evento, finché il contratto copre quell'evento). Alla stipula, se il proponente non copre la somma, la firma è rifiutata. A inizio evento, se non copre, nasce un debito.
- Clausole di impiego: tetto `ORE` o `QUEST` per evento, registrate come i servizi del protettore.
- Ferita grave del cliente (il mercenario): rimborso proponente → cliente, con conferma come sopra.
- Morte del cliente: rimborso agli eredi. In proposta si indica un personaggio erede (opzionale). Se c'è, dopo conferma staff il rimborso va all'erede; se non c'è, il movimento resta sul personaggio morto e lo staff lo gira a mano. Niente sistema successorio.

### Agente

- Alla stipula: credito creato per entrambi (`compenso_iniziale_cliente`, `compenso_iniziale_proponente`).
- Il contratto resta dormiente. Clausole accessorie descrivono attivazione, ricompense e condizioni.
- Azione **Attiva agente** del proponente. Se il modello ha `attivazione_richiede_staff`, parte solo dopo conferma staff. All'attivazione si erogano le ricompense delle clausole con momento `AD_ATTIVAZIONE` (una volta sola).
- Il contratto può restare stipulato fino a scadenza anche dopo l'attivazione, oppure chiudersi: flag di modello `risolvi_ad_attivazione`.

## UI giocatore

Tab `contratti` in `MainPage`, accanto alle altre tab a modulo.

- Elenco attivi e in attesa: controparte, ruolo (Proponente / Cliente), nome modello, tipologia, scadenza (data reale).
- Slot usati / slot totali. Con slot liberi, wizard «Nuova proposta».
- Proposta in attesa: QR, testo, annulla.
- Dal QR: testo completo, poi i due pulsanti. Se il cliente ha già quella tipologia, il pulsante di firma è disabilitato e compare il motivo.
- Pubblicitario: elenco post dell'evento associabili.
- Protettore / Mercenario: registra servizio, segnala ferita.
- Agente (proponente): attiva.

## Sync ed edge

Tutti i modelli di catalogo e di runtime sono `SyncableModel` (UUID, `sync_id`, `updated_at`, tombstone). I file non c'entrano: il QR è un id, il testo è nel DB.

Le erogazioni non si ricalcolano in apply. Si sincronizza l'adempimento già scritto e il `CreditoMovimento` collegato. I hook locali partono solo quando l'azione nasce su quel nodo (reclamo task, addebito forgiatura, chiusura evento, firma).

## Fasi di implementazione

1. **Fondamenta giocabili.** Modulo, modelli, sync, flag Korp, bonus carica, statistica SCT, tool staff per i modelli delle sei tipologie, tab, wizard, QR, firma/rifiuto, scadenza, adempimenti, pagamenti `ALLA_STIPULA` (protettore, agente, mercenario se previsto alla firma).
2. **Motori economici continui.** Talento sul reclamo task. Creatore sui tre ambiti di costo. Pubblicitario con associazione post e chiusura evento, debiti inclusi.
3. **Clausole vive.** Servizi ore/quest, ferita con conferma, morte con conferma staff, attivazione agente, compensi a inizio/fine evento e a scadenza.

`GENERICO` è usabile già in fase 1 per un contratto solo testuale con compenso alla stipula.

## Decisioni aperte

Se restano senza risposta, si implementa il default indicato nel resto del documento.

1. **Grado d'ingresso.** Base 3 indipendente dalla carica; `bonus_slot_contratto` default 0, da mettere a 1 sui gradi che aggiungono uno slot.
2. **Pubblicitario.** Il cliente chiude a `massimo × crediti_per_post`. Il proponente chiude a `post_validi_nel_tetto × cifra − mancanti × cifra`. L'indennizzo è un trasferimento, non credito creato.
3. **Saldo insufficiente.** Indennizzi e penali diventano debito, saldo non negativo. Il prezzo alla stipula, se scoperto, blocca la firma.
4. **Mercenario.** Paga il proponente al cliente. Il modello sceglie se alla stipula o a ogni inizio evento.
5. **Erede.** Personaggio opzionale indicato in proposta. Senza erede, il rimborso di morte resta sul PG morto.
6. **Ferita grave.** Azione sul contratto con conferma, non un nuovo stato di salute globale.
7. **Due Korp abilitate.** Gli slot si sommano.
8. **Conto.** I crediti creati vanno sul deposito. I trasferimenti tra PG usano il deposito.
