# Contratti — progettazione

Feature opzionale di gioco: un personaggio **proponente** (soggetto attivo) offre un contratto; un **cliente** (soggetto passivo) lo sottoscrive scansionando un QR. Entrambi sono i **contraenti**.

Il documento fissa il modello e gli automatismi. Le decisioni di gioco sono chiuse in fondo. Il testo operativo per lo staff, con gli esempi di impostazione, è la wiki solo staff `docs/wiki/staff/contratti.md`.

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

Uno **slot di contratto** è la capacità del proponente di tenere aperta una proposta o un contratto stipulato. I contratti liberi sono gli slot ancora aperti e contano solo i contratti come proponente. Il cliente non consuma slot. Il tetto del cliente è **uno stipulato per modello**: due modelli distinti si firmano entrambi, anche se nascono dallo stesso preset.

### Perché statistica + dati su Korp/Carica

La statistica dà alle abilità, agli oggetti e allo staff lo stesso canale già usato per RCT, RCO e gli altri modificatori (`AbilitaStatistica` → `get_valore_statistica`). I «3 in ingresso» e il «+1 per carica» restano dati di Korp e Carica, come oggi `bonus_crediti_evento` e `bonus_peso_influencer`: lo staff li cambia senza fabbricare un'abilità per ogni grado.

Formula effettiva, ricalcolata a ogni lettura (niente valore derivato salvato sul personaggio):

```text
slot = slot_contratto_base della Korp attiva
     + bonus_slot_contratto della carica su quella membership
     + get_valore_statistica("SCT")
```

Un personaggio ha una sola Korp. Non esiste una somma tra Korp.

- `Carriera.sottoscrive_contratti` (bool, default falso). Se falso, gli slot di quella Korp sono 0 e i suoi modelli non sono offrili.
- `Carriera.slot_contratto_base` (intero). Lo staff lo imposta **per Korp**. Il valore iniziale suggerito in scheda è 3, ed è solo un punto di partenza.
- `Carica.bonus_slot_contratto` (intero). Lo staff lo imposta **per carica**. Il valore iniziale è 0: il grado d’ingresso non aggiunge slot da solo. Una carica può valere +1, +2 o anche un malus.
- Statistica **SCT** «Slot di contratto», `is_numero`, valore base 0. È il solo addendo che abilità e oggetti modificano. Si somma solo se la Korp attiva sottoscrive.

Senza carica, il bonus carica è 0. Occupano uno slot gli stati `IN_ATTESA` e `STIPULATO`. Rifiuto, scadenza, risoluzione e annullamento lo liberano. Il proponente non firma la propria proposta.

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
6. Alla firma si controlla: modulo attivo, cliente diverso dal proponente, proposta ancora `IN_ATTESA`, e il cliente non ha già un `STIPULATO` dello stesso modello. Poi partono gli effetti con innesco `ALLA_STIPULA`.

La scadenza è pigra: ogni lettura e ogni hook che eroga un bonus marca `SCADUTO` se `now > scadenza`. Gli hook economici agiscono solo su `STIPULATO` ancora nel termine. Funziona anche sul nodo edge offline, senza un cron.

## Catalogo staff: composizione, non tipologie fisse

Tool staff **Contratti**. Le sei idee (Talento, Creatore, Pubblicitario, Protettore, Mercenario, Agente) sono **ricette di partenza**, non la forma del dato e non la forma della schermata. Lo staff crea un modello vuoto e lo compone. Un settimo contratto che riusa effetti già presenti non richiede una modifica al codice né una nuova maschera.

Tre livelli, dal più stabile al più estensibile:

| Livello | Chi lo cambia | Cosa contiene |
|---------|----------------|---------------|
| Modello | Staff, a runtime | Nome, Korp, testo, durata, parametri, esclusività, effetti agganciati, clausole, compensi |
| Effetto | Registry in codice | Un comportamento riutilizzabile (es. «percentuale sulla task del cliente») con i suoi campi |
| Innesco | Punto nel codice di gioco | Il momento in cui gli effetti di quel tipo vengono valutati (firma, task, costo, fine evento, …) |

La UI dello staff è generata dal registry: elenco effetti, e per ciascuno i campi dichiarati. Aggiungere un effetto nuovo al registry lo fa comparire nel menu «Aggiungi effetto» senza un’altra pagina.

### ModelloContratto

| Campo | Ruolo |
|-------|--------|
| `campagna`, `korp` | Offerta di quella Korp, in quella campagna. |
| `nome`, `attivo` | Voce nel wizard del proponente. |
| Limite cliente | Un solo `STIPULATO` per `ModelloContratto`. La chiave di esclusività dei preset non blocca più la firma. |
| `durata_modo` | `GIORNI` (N giorni reali) oppure `FINE_EVENTO` (scadenza = `data_fine` dell'evento scelto in proposta; deve esistere un evento). |
| `durata_giorni` | Usato se `GIORNI`. |
| `testo` | Testo mostrato alla firma, con segnaposto. |

Non c’è un campo tipologia obbligatorio. Un’etichetta visibile al giocatore, se serve, è il `nome` del modello.

### Parametri del modello

Lo staff aggiunge righe, senza schema precompilato dalla tipologia:

| Campo riga | Ruolo |
|------------|--------|
| `chiave` | Slug stabile (`pct_cliente`, `tema`, `somma`). |
| `etichetta` | Ciò che vede il proponente. |
| `tipo` | `INTERO`, `DECIMALE`, `PERCENTUALE`, `TESTO`, `SCELTA`, `PERSONAGGIO`. |
| `chi_compila` | `STAFF` (valore fisso sul modello) oppure `PROPONENTE` (in proposta). |
| `min`, `max`, `default`, `scelte` | Vincoli. Per `PERSONAGGIO` il proponente sceglie un PG (l’erede, per esempio). |

Un numero dentro un effetto può essere una costante oppure il riferimento `{{param:chiave}}`. Così lo stesso effetto «percentuale sulla task» serve un Talento 10/20 fisso e un Talento in cui il proponente sceglie la percentuale tra 5 e 25.

### Effetti agganciati

Sul modello, «Aggiungi effetto» elenca il registry. Ogni riga salva `codice_effetto` + `config` (costanti e riferimenti a parametri). Le righe hanno un ordine. Lo snapshot della proposta copia le righe già risolte (niente `{{param:…}}` vivo).

Clausole e compensi sono lo stesso meccanismo, in due elenchi che il giocatore riconosce:

- **Clausola accessoria:** nome, testo, obbligatoria o a scelta del proponente, più zero o più effetti che valgono solo se la clausola è nel contratto firmato.
- **Compenso accessorio:** nome, testo, e di norma un effetto `credito_creato` o `trasferimento`. È una clausola con presentazione da compenso, così lo staff non ha un terzo editor.

Gli effetti del modello valgono sempre. Quelli di una clausola o di un compenso valgono se quella voce è stata scelta. Tutto finisce nello snapshot.

### Registry effetti (prima dotazione)

Gli importi sono crediti. Il credito **creato** va sul deposito, come le task. Il versamento tra contraenti è un trasferimento sullo stesso conto. Ogni erogazione scrive `ContrattoAdempimento` con chiave unica `(contratto, codice_effetto, fonte)`. Il movimento nasce una volta e viaggia nel sync; l’altro nodo non lo ricalcola.

| Codice | Innesco | Config che lo staff compila | Cosa fa |
|--------|---------|-----------------------------|---------|
| `credito_creato` | stipula, inizio evento, fine evento, scadenza, attivazione, manuale | beneficiario `CLIENTE` / `PROPONENTE` / `ENTRAMBI`, importo | Accredita credito nuovo. |
| `trasferimento` | gli stessi | da, a, importo, se scoperto `BLOCCA` (solo in firma) o `DEBITO` | Sposta crediti. Il saldo non va sotto zero: il resto resta debito sull’adempimento. |
| `percentuale_task` | il cliente reclama una task | `pct_cliente`, `pct_proponente` | Sulla cifra crediti già accreditata (dopo fattore Korp): bonus a entrambi. Il prestigio non entra. Le task del proponente non contano. |
| `sconto_costo` | addebito di un costo | ambiti spuntabili (`creazione_infusione`, `creazione_cerimoniale`, `creazione_tessitura`, `forgiatura`, `consumabile`), `pct_sconto_cliente`, `pct_bonus_proponente` | Base = costo pieno, prima di RCT. Il cliente paga `max(0, pieno − RCT − sconto contratto)`. Il proponente riceve la percentuale sul pieno. |
| `post_tetto_evento` | fine evento | `massimo_post`, `crediti_per_post` | Vedi la ricetta Pubblicitario. Il giocatore associa i post perché l’effetto è presente, non perché il modello si chiama Pubblicitario. |
| `contatore_servizi` | registrazione manuale | unità `ORE` o `QUEST`, `massimo_per_evento` | Conta prestazioni. Non paga da solo. |
| `penale_confermata` | ferita segnalata, oppure `data_morte` | evento `FERITA` o `MORTE`, da, a, importo, conferma `CONTROPARTE` o `STAFF`, a morte paga `CLIENTE` o `EREDE` | Nasce un adempimento in attesa. Dopo la conferma parte il trasferimento, con debito se il saldo non basta. La morte non paga al solo salvataggio di `data_morte`. |
| `attivazione` | azione del proponente | `richiede_staff`, `risolvi_contratto` | Sblocca gli effetti con innesco attivazione, una volta. Opzionalmente porta il contratto a `RISOLTO`. |

Un contratto solo testuale è un modello con zero effetti: testo, ed eventualmente clausole senza effetti. Non serve una tipologia `GENERICO`.

Un contratto futuro si fa in tre modi:

1. **Solo staff.** Nuova combinazione di effetti già in elenco, parametri nuovi, testo nuovo. Esempio: un «Patrono» che è `trasferimento` alla stipula più `percentuale_task` più `penale_confermata` in morte.
2. **Una riga di registry.** Serve un innesco che il gioco non ha ancora (vittoria a un duello di carte, acquisto in negozio, …). Si aggiunge un codice effetto e la chiamata nel punto giusto del codice. La maschera staff è la stessa.
3. **Mai** una settima maschera «tipo di contratto» con i campi cuciti dentro il componente.

I hook di gioco non guardano il nome del modello. Cercano i contratti `STIPULATO` del personaggio e eseguono le righe snapshot il cui codice corrisponde all’innesco.

```text
reclama_ricompensa(cliente, crediti)
  → effetti snapshot con codice percentuale_task

addebito costo(cliente, ambito, pieno, fonte)
  → effetti snapshot con codice sconto_costo e ambito incluso

termina evento
  → effetti snapshot con codice post_tetto_evento, credito_creato/trasferimento a fine evento
```

## Ricette iniziali

Sono preset opzionali («Crea da esempio» nello staff), espressi solo con il registry. Lo staff può duplicarli e cambiarli.

### Talento

Effetto `percentuale_task` con `pct_cliente` e `pct_proponente`. Chiave `talento`. Esempio 10 e 20 su una task da 100: il cliente prende altri 10, il proponente 20, oltre i 100 già suoi.

### Creatore

Effetto `sconto_costo` sugli ambiti scelti. Chiave `creatore`. Forgiatura con pieno 600 e 10% / 10%: il cliente paga 60 in meno, il proponente riceve 60. Con RCT lo sconto si somma e il pagamento resta ≥ 0; il bonus del proponente resta sul pieno.

### Pubblicitario

Parametro `tema` compilato dal proponente. Effetto `post_tetto_evento`. Chiave `pubblicitario`.

Il proponente associa un proprio `SocialPost` dell’evento. Un post conta per un solo contratto che ha questo effetto. Lo staff può scollegarlo. Nessun match sul testo del post.

A Termina evento, per ogni contratto ancora valido (`data_inizio`/`data_fine` dell’evento dentro la vita del contratto):

```text
n        = min(post associati validi, massimo)
mancanti = massimo − n
importo  = crediti_per_post

cliente    += n * importo          (credito creato)
proponente += n * importo          (credito creato)
se mancanti > 0:
    trasferimento proponente → cliente di mancanti * importo
```

Con massimo 3 e 30 a post: 2 post → netto cliente 90, netto proponente 30; 5 post → entrambi 90; 0 post → il proponente versa 90 e non si crea credito. La tab mostra l’anteprima prima della chiusura. Idempotente per `(contratto, evento)`.

### Protettore

- `trasferimento` cliente → proponente alla stipula (`se_scoperto = BLOCCA`).
- `contatore_servizi` ore o quest per evento.
- `penale_confermata` ferita: rimborso proponente → cliente, conferma della controparte o dello staff.
- `penale_confermata` morte: penale, conferma staff.

Chiave `protettore`. La ferita è un’azione sul contratto: non esiste un modello ferite in scheda.

### Mercenario

Stessi mattoni, versi invertiti. `trasferimento` proponente → cliente alla stipula oppure a ogni inizio evento (`BLOCCA` in firma, `DEBITO` a inizio evento). `contatore_servizi` come clausola di impiego. Ferita e morte del cliente con `penale_confermata`; in morte il beneficiario può essere l’erede (`parametro` di tipo `PERSONAGGIO`). Senza erede il movimento resta sul PG morto. Chiave `mercenario`.

### Agente

- `credito_creato` per entrambi alla stipula.
- `attivazione` (con o senza conferma staff, con o senza risoluzione).
- Clausole con effetti `credito_creato` / `trasferimento` a innesco attivazione: sono le ricompense e le condizioni economiche. Il testo della clausola porta il resto.

Chiave `agente`.

Segnaposto nel testo del modello: `{{proponente}}`, `{{cliente}}`, `{{korp}}`, `{{scadenza}}`, `{{parametri}}`, `{{clausole}}`, `{{compensi}}`. Lo snapshot risolve i valori noti; il nome del cliente entra solo alla firma.

## UI giocatore

Tab `contratti` in `MainPage`, accanto alle altre tab a modulo.

- Elenco attivi e in attesa: controparte, ruolo (Proponente / Cliente), nome modello, scadenza (data reale).
- Slot usati / slot totali. Con slot liberi, wizard «Nuova proposta» (modelli della Korp, parametri lasciati al proponente, clausole e compensi ammessi).
- Proposta in attesa: QR, testo, annulla.
- Dal QR: testo completo, poi i due pulsanti. Se il cliente ha già uno stipulato di quello stesso modello, la firma è disabilitata e compare il motivo.
- Le azioni extra dipendono dagli effetti nello snapshot, non dal nome del modello: associa post se c’è `post_tetto_evento`, registra servizio se c’è `contatore_servizi`, segnala ferita se c’è `penale_confermata` su `FERITA`, attiva se c’è `attivazione`.

## Sync ed edge

Tutti i modelli di catalogo e di runtime sono `SyncableModel` (UUID, `sync_id`, `updated_at`, tombstone). I file non c'entrano: il QR è un id, il testo è nel DB.

Le erogazioni non si ricalcolano in apply. Si sincronizza l'adempimento già scritto e il `CreditoMovimento` collegato. I hook locali partono solo quando l'azione nasce su quel nodo (reclamo task, addebito forgiatura, chiusura evento, firma).

## Fasi di implementazione

1. **Editor e ciclo di firma.** Modulo, sync, flag Korp, bonus carica, statistica SCT, editor staff a composizione (parametri, effetti, clausole, compensi, preset delle sei ricette), tab, wizard, QR, firma/rifiuto, scadenza. Effetti di fase 1: `credito_creato` e `trasferimento` agli inneschi di stipula. Un modello con zero effetti è già un contratto solo testuale.
2. **Inneschi continui.** `percentuale_task` sul reclamo, `sconto_costo` sugli addebiti, `post_tetto_evento` a fine evento, debiti inclusi.
3. **Azioni dei contraenti.** `contatore_servizi`, `penale_confermata` (ferita e morte), `attivazione`, inneschi a inizio/fine evento e a scadenza.

## Decisioni chiuse

1. **Slot.** Impostati dallo staff, diversi per Korp (`slot_contratto_base`) e per carica (`bonus_slot_contratto`). Nessun +1 automatico sul grado d’ingresso. Un personaggio non può essere in due Korp: conta la sola membership attiva, più la statistica SCT.
2. **Pubblicitario.** Il cliente chiude sempre a `massimo × crediti_per_post`. Il proponente chiude a `post nel tetto × cifra − post mancanti × cifra`. L’indennizzo è un trasferimento del proponente verso il cliente. Se il saldo non copre, il resto è debito e il saldo non va sotto zero.
3. **Mercenario.** Paga il proponente. Il modello sceglie se alla stipula o a ogni inizio evento. L’erede è un personaggio opzionale indicato in proposta; senza erede il rimborso di morte resta sul PG morto.
4. **Ferita grave.** Azione sul contratto, con conferma. Non è uno stato di salute in scheda.
5. **Conto.** Tutti i bonus (crediti creati dal sistema) vanno sul conto deposito: sono guadagni extra. Anche i trasferimenti tra contraenti (prezzo, indennizzo, penale, rimborso) usano il deposito.

## Istruzioni staff

Pagina wiki solo staff, sezione Operatività tecnica: `docs/wiki/staff/contratti.md` (slug `staff-contratti`). Spiega modulo, slot per Korp e carica, ogni effetto con i campi, e le ricette con i numeri (Talento 10/20, Creatore su 600, Pubblicitario 3×30, Protettore, Mercenario, Agente, più un contratto nuovo composto senza codice).
