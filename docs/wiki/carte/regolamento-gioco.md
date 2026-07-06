# Cronache delle Sette Elegie — Regole di gioco

> **Riferimento ufficiale** per giocatori e master. Le keyword operative si configurano in staff; l’app automatizza gradualmente quanto indicato in [Stato implementazione nell’app](#stato-implementazione-nellapp-kor35).

## Obiettivo

Sfida un avversario riducendo i suoi **punti vita** da **20 a 0**. Ogni giocatore rappresenta un comandante le cui scelte si traducono in carte **Personaggio**, **Equipaggiamento**, **Terra** ed **Effetto**.

---

## Tipi di carta

| Tipo | Nome in app | Comportamento |
|------|-------------|---------------|
| **Personaggio** | PG | Permanente. Combatte, può portare un equipaggiamento. |
| **Equipaggiamento** | OGG | Permanente. Si attacca a un personaggio; muore con lui. |
| **Terra** | LUO | Permanente. Occupa lo slot terra condiviso; modifica le regole per entrambi. |
| **Effetto** | EVT | Monouso: si risolve e va allo **scarto**. |

**Permanenti** = personaggi, equipaggiamenti e terre.

---

## Le sette Aure (energie)

Ogni carta (tranne le terre) ha un’**aura** — nel sistema KOR35 corrisponde al campo **energia** della carta:

| Colore | Aura | Famiglia |
|--------|------|----------|
| Blu | **Marziale** | Naturale |
| Giallo | **Tecnologica** | Naturale |
| Arancione | **Innata** | Naturale |
| Nero | **Magica** | Soprannaturale |
| Bianco | **Sacra** | Soprannaturale |
| Viola | **Psionica** | Soprannaturale |
| Verde | **Arcana** | Soprannaturale |

Le **terre non hanno aura**.

### Costruzione mazzo — regole aura

- Il mazzo ha **15 carte** + **1 Leader** (comandante) scelto a parte.
- Nel mazzo possono comparire al massimo **3 aure diverse**:
  - almeno **1 naturale** (Marziale, Tecnologica o Innata);
  - almeno **1 soprannaturale** (Magica, Sacra, Psionica o Arcana);
  - una **terza** a scelta (qualsiasi famiglia).
- Per giocare un **effetto** o un **equipaggiamento** di una certa aura, devi avere **almeno un personaggio** di quella aura nel mazzo (non necessariamente in campo).
- L’**aura primaria** è l’energia del **Leader** scelto in setup: definisce il bonus «color pie» del mazzo per tutta la partita.

### Altre regole mazzo

| Regola | Valore |
|--------|--------|
| Carte nel mazzo | **15** (oltre al Leader) |
| Personaggi nel mazzo | **minimo 8** |
| Terre nel mazzo | **massimo 2** |
| Copie stessa carta | **1** (salvo carta marcata duplicabile: max **2**) |

---

## Statistiche dei personaggi

Ogni personaggio in campo ha tre statistiche:

| Statistica | Significato |
|------------|-------------|
| **Forza** | Danni inflitti quando attacca. |
| **Robustezza** | Danni che può subire prima di morire. Se i danni accumulati ≥ Robustezza → il personaggio **muore**. |
| **Iniziativa** | Velocità in combattimento (vedi [Combattimento](#combattimento)). |

> Nell’app, **Forza** ≈ campo `attacco`, **Robustezza** ≈ campo `salute` della carta. **Iniziativa** è usata nel combattimento automatizzato (eroi e Leader).

---

## Campo di gioco

### Per giocatore

- **Leader**: Personaggio comandante scelto a parte; all’apertura occupa uno slot eroe (max 2 PG in campo). Il flag «è Leader» in partita abilita effetti mirati (es. equip). Se muore, torna in **mano**.
- **Personaggi**: massimo **2** in campo.
- **Equipaggiamenti**: massimo **1** per personaggio. Il JSON `bonus_equip` sulla carta Oggetto può dare bonus in combattimento (Forza/Robustezza/Iniziativa), anche condizionati al flag **è Leader** (`robustezza_se_leader` o `{"duello":[…,"se_leader":true]}`).
- **Mano**, **mazzo**, **scarto** privati.
- **Punti vita**: 20.

### Terra (slot centrale)

- Esiste **un solo slot terra**, **condiviso** tra i due giocatori.
- Giocare una terra **sostituisce** quella presente.
- Gli effetti della terra valgono in modo **simmetrico** per entrambi, salvo testo carta diverso.

> Nell’app MVP la terra è uno slot **condiviso** (`terra_condivisa`); giocarne una nuova sostituisce la precedente (la vecchia va allo scarto di chi l’aveva giocata).

---

## Mana ed economia del turno

Ogni giocatore ha un **contatore di mana** personale.

| Turno di gioco | Mana disponibile per giocare |
|---------------|------------------------------|
| 1° turno | 1 |
| 2° turno | 2 |
| 3° turno e successivi | 3 (massimo) |

- Il mana **si rinnova** all’inizio del tuo turno (non si accumula oltre il massimo del turno).
- Ogni carta ha un **costo** in mana (0–3 nel catalogo attuale).

### Cosa puoi giocare per turno

Fino a **1 permanente** + **1 effetto**, pagando il mana, con questa struttura:

1. **Fase iniziale** (opzionale): gioca **una terra** **oppure** un **equipaggiamento** — consuma la tua giocata **permanente** del turno.
2. **Fase effetto** (opzionale): gioca **un effetto** (monouso → scarto).
3. **Fase combattimento**: i tuoi personaggi **non esauriti** possono attaccare (vedi sotto). Attaccare **esaurisce** («stappa») il personaggio.
4. **Fase finale** (opzionale): se non hai ancora giocato il **permanente** e/o l’**effetto** e hai mana sufficiente, puoi farlo ora.

Inoltre, all’inizio del tuo turno: **peschi 1 carta**.

### Rigenerazione a fine turno

Un personaggio **non esaurito** che ha subito danni **si cura completamente** a **fine turno** (i segnalini danno vengono rimossi; non muore finché i danni del turno non raggiungono la Robustezza in un singolo scambio).

---

## Combattimento

Il giocatore di turno può far attaccare i propri personaggi schierati e **non esauriti**.

### Bersaglio

- Un **personaggio avversario** schierato, oppure
- Il **giocatore avversario** (punti vita).

### Personaggio vs giocatore

Il difensore perde punti vita pari alla **Forza** dell’attaccante.

### Personaggio vs personaggio

I due si scambiano danni pari alla rispettiva **Forza**, applicando le regole di **Iniziativa**:

| Situazione | Risoluzione |
|------------|-------------|
| Iniziativa **diversa** | Chi ha iniziativa **maggiore** infligge danni **per primo**. Se il bersaglio muore, **non contrattacca**. |
| Iniziativa **pari** | I danni sono **simultanei**. |

I danni su un personaggio persistono fino a fine turno (poi cura se non esaurito) o fino a morte se Robustezza raggiunta.

### Esaurimento (tapped)

Un personaggio che attacca diventa **esaurito** e non può attaccare di nuovo finché non viene «ristappato» dalle regole del gioco (es. inizio del tuo prossimo turno — da definire nel dettaglio se diverso da MTG).

### Difensore

Abilità **Difensore** (keyword): finché è in campo, l’avversario deve attaccare **prima** il difensore — non può colpire l’altro personaggio né il giocatore finché il difensore resta in campo.

---

## Keyword e abilità comuni

| Keyword | Effetto (sintesi) |
|---------|-------------------|
| **Mutazione [X]** | Quando questo personaggio muore, puoi mettere in gioco al suo posto un personaggio dalla mano con costo ≤ X. |
| **Colpo [X]** | Infligge X danni a un personaggio o al giocatore. |
| **Ferita [X]** | Come Colpo, con scelta bersaglio (personaggio). |
| **Guscio [X]** | Il personaggio ha X segnalini guscio; quando sta per morire, perde un guscio invece di morire. |
| **Guarigione** | A fine turno, cura personaggi (testo carta: tutti / alleati / sé). |
| **Difensore** | Obbliga gli attacchi avversari su di sé. |
| **Sinergia** | Bonus se controlli due personaggi con sinergia (testo carta). |
| **Pesca [X]** | Pesca X carte (tipicamente a inizio turno se in campo). |
| **Rigenerazione [X]** | Guadagni X mana (effetto monouso o trigger). |

Le definizioni precise e i parametri sono nel catalogo keyword staff e nel testo delle carte.

---

## Color pie — bonus aura primaria (Leader)

Se l’aura del Leader è **primaria** nel mazzo, applichi il bonus globale:

| Aura | Colore | Bonus primaria |
|------|--------|----------------|
| **Sacra** | Bianco | +2 Robustezza a tutti i tuoi personaggi. Stile: difesa, guarigione, protezione. |
| **Magica** | Nero | −1 al costo degli **Effetti**. Stile: distruzione, danni diretti, personaggi fragili. |
| **Psionica** | Viola | +1 Iniziativa a tutti i tuoi personaggi. Stile: personaggi deboli, guscio, controllo, tutoraggio. |
| **Arcana** | Verde | +1 mana massimo per turno (fino a **4**). Stile: sinergie, effetti potenti. |
| **Marziale** | Blu | +1 Forza a tutti i tuoi personaggi. Stile: attacco, difensori da combattimento. |
| **Innata** | Arancione | −1 al costo di tutti i **Personaggi**. Stile: corpi bilanciati, molte abilità (es. Mutazione). |
| **Tecnologica** | Giallo | −1 al costo di tutti gli **Equipaggiamenti**. Stile: difesa, equip forti, scaling con equip. |

---

## Glossario rapido

| Termine | Significato |
|---------|-------------|
| **Leader / Comandante** | Carta comandante, parte in campo, aura primaria. |
| **Permanente** | PG, equip o terra sul campo. |
| **Esaurito / Stappato** | Personaggio che ha già attaccato nel turno. |
| **Influenza** | Nome legacy in app per i punti vita del giocatore (20). |
| **Mana / Energia** | Risorsa per giocare carte. |

---

## Stato implementazione nell’app KOR35

L’app supporta oggi un **MVP duello live**. La tabella seguente confronta le regole di questa pagina con il codice attuale (aggiornare dopo ogni release).

| Regola | Target | App oggi |
|--------|--------|----------|
| 15 carte in mazzo | Sì | ✅ Validato |
| Min 8 personaggi nel mazzo | Sì | ✅ Validato |
| Max 2 terre nel mazzo | Sì | ✅ Validato |
| Leader separato + in campo (slot eroe) | Sì | ✅ Slot 0; flag `eroi_is_leader` |
| Max 3 aure (1 nat + 1 sopra + 1 opz.) | Sì | ✅ Validato (min 1 nat + 1 sopra) |
| Punti vita 20 | Sì | ✅ `influenza_*` |
| Max 2 personaggi in campo | Sì | ✅ |
| Max 1 equip per personaggio | Sì | ✅ Bonus `bonus_equip` in combattimento (`se_leader`) |
| Terra slot **condiviso** | Sì | ✅ `terra_condivisa` |
| Effetti monouso → scarto | Sì | ✅ |
| Mana 1 → 2 → 3 (rinnovo) | Sì | ✅ Curva per turno; max dinamico per giocatore |
| Max mana 4 (Leader Arcana) | Sì | ✅ `mana_massimo` da aura Leader |
| 1 permanente + 1 effetto / turno | Sì | ✅ `turno_flags`; fine turno con «Passa» |
| Pesca 1 / turno | Sì | ✅ (+ mano iniziale 4) |
| Forza / Robustezza | Sì | ✅ `attacco` / `salute` + bonus Leader (Marziale/Sacra/Psionica) |
| Iniziativa in combattimento | Sì | ✅ Ordine danni PG vs PG |
| Attacco esaurisce | Sì | ✅ `eroi_esauriti`; ristappo a inizio turno |
| Cura fine turno se non esaurito | Sì | ✅ Robustezza piena a fine turno |
| Difensore | Sì | ✅ Keyword nel testo; bersaglio obbligatorio |
| Leader muore → mano | Sì | ✅ Torna in mano (non scarto) |
| Aura primaria = energia Leader (setup) | Sì | ✅ `aura_primaria`; bonus color pie globali |
| Keyword automatizzate | Parziale | ✅ EffectScript: Mutazione, Colpo, Ferita, Pesca, Rigenerazione, catena FIFO |
| Lobby OPEN + QR + prematch | Sì | ✅ |
| Reliquiario / bustine | Sì | ✅ |

### È implementabile?

**Sì**, in fasi. Il motore attuale (stato duello, tipi carta, keyword script, WS) è la base giusta. Roadmap tecnica suggerita:

1. **Regolamento e mazzo** — Leader, aura primaria (validazione mazzo ✅).
2. **Mana e turno** — Curva 1/2/3, fasi (permanente/effetto/combattimento), limiti giocate.
3. **Combattimento** — Iniziativa, scambio danni, esaurimento, Difensore, cura fine turno ✅.
4. **Campo** — Terra condivisa; morte Leader → mano ✅.
5. **Color pie** — Bonus passivi da Leader.
6. **Keyword** — Guscio, Guarigione, Sinergia, ecc. via EffectScript o regole hardcoded.

La modalità **manuale** in app resta utile finché ogni fase non è automatizzata.

---

*Sorgente: `docs/wiki/carte/regolamento-gioco.md` — slug `carte-regolamento-gioco`. Sync: `make wiki-carte-sync ENV=… WIKI_CARTE_FORCE=1`.*
