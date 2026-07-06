# Regolamento carte — accesso e app

> **Regole complete di gioco:** vedi la pagina **[Regole di gioco — Sette Elegie](carte-regolamento-gioco)** (mazzo, mana, combattimento, color pie).

## Obiettivo (sintesi)

**Cronache delle Sette Elegie** è il gioco di carte collezionabili di KOR35: collezione, reliquiario, bustine e **duelli** tra personaggi giocanti. Vince chi porta l’avversario a **0 punti vita** (partenza **20**).

## Dove leggere le regole

| Pagina Wiki | Contenuto |
|-------------|-----------|
| **Regole di gioco** | Regolamento completo (mazzo, Leader, mana, combattimento, aure) |
| *Questa pagina* | Collezione, duello in app, keyword, economia bustine |

## Collezione ed espansioni

- **Espansioni**: set tematici di carte e bustine dedicate.
- **Bustine**: acquisto con crediti in-game o QR evento.
- **Rarità**: Comune → Non comune → Rara → Epica → Leggendaria → Unica.

## Mazzo da duello (validazione app)

L’app controlla il mazzo da **15 carte** (il **Leader** è scelto a parte — vedi [regolamento di gioco](carte-regolamento-gioco)):

- **15 carte** esattamente nel mazzo selezionato.
- **1 Leader** (Personaggio comandante) scelto a parte — non fa parte delle 15 carte.
- Almeno **8 Personaggi**.
- Massimo **2 Terre**.
- Massimo **3 aure diverse** (le Terre non contano nell’aura).
- Almeno un’aura **Naturale** (Marziale, Tecnologica, Innata) e una **Soprannaturale** (Magica, Sacra, Psionica, Arcana).
- Per giocare **Equipaggiamenti** o **Effetti** di un’aura serve almeno un **Personaggio** di quell’aura nel mazzo.
- Copie: **1** (o **2** se la carta è `duplicabile`).

Le regole di gioco complete (Leader, mana, combattimento) sono nel [regolamento di gioco](carte-regolamento-gioco).

## Duello in app

- **Influenza** (= punti vita): 20 per giocatore.
- Turni alternati; azioni principali: gioca carta, attacca, passa, rispondi a effetti (`effect_choice`).
- Sync in tempo reale (WebSocket).

### Avvio partita

| Modalità | Come si inizia |
|----------|----------------|
| **TEST** | Sfida da lista avversari (tab Carte). |
| **OPEN** | **Apri scontro** → QR sessione → avversario si unisce → **prematch** (mazzo, posta, pronto) → partita. |

Posta opzionale in CR. Modalità **live** (turni in app) o **manuale** (tavolo fisico, stato aggiornato a mano).

## Reliquiario

- **5 slot** per bonus passivi fuori dal duello (`bonus_equip`).
- **Legami** tra carte con stesso `legame_id` o set.

## Keyword

Parole chiave nel testo carta (grassetto in app). Parametri `[X]`, `[Y]`, …

Esempi automatizzati in duello live: **Mutazione**, **Colpo**, **Ferita**, **Pesca**, **Rigenerazione** (EffectScript v1).

Master: Wiki *Keyword carte — guida master* e *EffectScript v1*.

## Economia bustine

- Limite giornaliero e **pity** configurabili da staff.
- Pool bustina limitato all’**espansione** collegata.

## Catalogo demo

Venticarte di esempio + bustina «Sette Elegie — bustina demo»:

```bash
make seed-carte-esempio ENV=dev-home
```

---

*Sync sorgenti: `make wiki-carte-sync ENV=…` — vedi `docs/wiki/carte/README.md`.*
