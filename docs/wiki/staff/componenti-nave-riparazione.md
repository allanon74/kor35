# Componenti nave, stiva e riparazione QR

Runbook staff per il sistema **componenti** (riparazione sottosistemi), **stiva globale**, **coppie opposte**, **compattatore** e **aggiornamento codici eventi** da stato nave.

Fonte tecnica: moduli `pilotaggio/componenti_stiva.py`, `pilotaggio/componenti_riparazione.py`, `pilotaggio/evento_codici.py`, `pilotaggio/compattatore_engine.py`.

---

## Panoramica

| Concetto | Descrizione |
|----------|-------------|
| **Componenti** | Mattoni aura `0CP` (Componenti Nave), indice 0–9, uno per statistica; colore = caratteristica |
| **Stiva** | Inventario **globale nave** (condiviso), sync edge |
| **Coppie opposte** | 5 coppie di colori; coesistenza max **5 tick** pilota, poi annichilamento 1:1 in un colpo |
| **Riparazione QR** | Dopo `0RI` + minigioco: consumo componenti se abilitato (globale + per sottosistema) |
| **Compattatore Z** | Sottosistema tipo `compattatore`; console `/pilot/?screen=compattatore` |

---

## Setup iniziale catalogo

Dopo migrate su **ogni nodo** (master e replica), una tantum:

```bash
make seed-componenti-nave ENV=dev-home
```

Equivalente Docker:

```bash
cd config/docker
docker compose -f compose.base.yml -f compose.dev-home.yml exec -T backend \
  python manage.py seed_componenti_nave
```

Crea i **placeholder** (idempotente — non sovrascrive nomi esistenti):

- Aura **0CP** «Componenti Nave»
- 10 colori (`0C0`…`0C9`), 10 statistiche componente (`0K0`…`0K9`)
- 10 mattoni placeholder indice 0–9 (nome `Componente N — placeholder (Colore)`)
- 5 coppie opposte colore (Nero↔Bianco, Rosso↔Verde, …)

Opzioni make:

| Variabile | Effetto |
|-----------|---------|
| `COMPONENTI_NAVE_SKIP_IF_COMPLETE=1` (default) | Esce senza modifiche se i 10 mattoni ci sono già |
| `COMPONENTI_NAVE_SKIP_IF_COMPLETE=0` | Integra record mancanti (colori, coppie, …) |
| `COMPONENTI_NAVE_FORCE_COPPIE=1` | Ricrea le coppie opposte |

Per ricreare solo le coppie: `COMPONENTI_NAVE_SKIP_IF_COMPLETE=0 COMPONENTI_NAVE_FORCE_COPPIE=1 make seed-componenti-nave ENV=dev-home`

---

## Fasi di implementazione

| Fase | Contenuto | Stato |
|------|-----------|-------|
| **1 — Catalogo e stiva** | Aura `0CP`, placeholder 10 mattoni, `StivaComponenteNave`, coppie opposti, annichilamento al tick, API staff stiva | ✅ |
| **2 — Riparazione QR** | Toggle runtime staff, flag per sottosistema, requisiti JSON, estensione API `qr-repair` con `componenti_scelti[]`, **picker in modale QR giocatore** | ✅ |
| **3 — Compattatore** | Sottosistema tipo `compattatore`, energia da livello Z, compressione 2:1 e decompressione 1:2, console `/pilot/?screen=compattatore`, aggiornamento codici eventi da stato nave | ✅ |
| **4 — Risonanza** | Operazione risonanza (slot A/B, glitch, bonus), endpoint e pulsante console | ✅ |
| **5 — Giocatore e scheda** | Picker QR, tab Stiva nave (`0IN` > 0), Compattatore Quantico (flag evento) | ✅ |

### Cosa è la fase 2

La **fase 2** abilita la **riparazione sottosistemi a componenti** lato staff e backend:

- Toggle globale «Riparazione sottosistemi con componenti» in Runtime Console
- Per ogni sottosistema: checkbox «Riparazione QR richiede componenti» + JSON requisiti
- L’API `POST /api/pilot/subsystems/qr-repair/` valida e consuma componenti dalla stiva nave
- Tab staff **Stiva componenti** per caricare/scaricare inventario

### Cosa è la fase 5

Completata la parte **giocatore** e l’operazione opzionale **Compattatore Quantico**:

- Tab **Stiva nave** in app (`0IN` > 0): inventario globale in sola lettura
- Picker componenti nella modale QR riparazione (già in fase 2)
- **Compattatore Quantico**: sacrificio oggetto → 1–5 componenti; **spento di default** (`compattatore_quantico_abilitato=false`) — vedi sotto

### Cosa è la fase 3

La **fase 3** introduce la **console compattatore** (sottosistema Z):

- Modello `CompattatoreStatoNave` e accumulo energia a ogni tick pilota (`livello_Z` → soglia 9 per operazione)
- Operazioni **compressione** (2→1 indice superiore, anello 0↔9) e **decompressione** (1→2 indice inferiore)
- Console dedicata `/pilot/?screen=compattatore` e toggle staff «Console compattatore»
- Pulsanti staff **Anteprima / Aggiorna codici da stato nave** per eventi di volo (soluzione totale, parziali, catastrofi)

La risonanza (fase 4) è già attiva sulla stessa console.

---

## Configurazione staff (Pilotaggio)

### Runtime Console

Tab **Runtime Console** → Gestione Pilotaggio:

| Toggle | Effetto |
|--------|---------|
| Riparazione sottosistemi con componenti | Master switch consumo stiva su QR repair |
| Annichilamento colori opposti in stiva | Tick coesistenza + annichilamento |
| Console compattatore | Abilita `/pilot/?screen=compattatore` |
| **Compattatore Quantico** | **Default OFF.** Abilita sacrificio oggetto → componenti in console; lasciare spento fino all’evento live |
| Login compattatore | Richiede autenticazione console |
| Statistica accesso compattatore | Default `0IN` (creare stat in admin se assente) |

### Sottosistemi

Nel modal **Modifica sottosistema**:

- **Riparazione QR richiede componenti** — solo se il toggle globale è attivo
- **Requisiti riparazione (JSON)** — esempio:

```json
[
  {"tipo": "specifico", "mattone_id": "<uuid>", "quantita": 2},
  {"tipo": "scelta", "mattone_ids": ["<uuid-giallo>", "<uuid-verde>"], "quantita": 3}
]
```

- Tipo sottosistema **compattatore** — lettera `Z` (o altro codice scelto)

### Stiva componenti

Tab **Stiva componenti**: visualizza inventario, stato coppie opposte (`Coesistenza N/5`), pulsanti **+1** / **-1** per mattone.

### Eventi viaggio — aggiorna codici

Tab **Eventi viaggio** → **Aggiorna codici da stato nave**:

Allinea per ogni evento attivo:

- **Soluzione totale** (`codice_soluzione_esatta`) — livello attuale del sottosistema primario (da regole ST)
- **Soluzioni parziali** (`codici_soluzione_parziale`) — pattern da condizioni SP
- **Catastrofi** (`codici_precipizio`) — pattern da condizioni CA

Fonte stato: sessione console attiva (idle/volo) se presente, altrimenti registro nave persistente.

API: `POST /api/pilot/staff/eventi/aggiorna-codici-da-stato/` body opzionale `{ "evento_id": "...", "dry_run": false, "solo_attivi": true }`.

Usa **Anteprima** (`dry_run: true`) per verificare i codici senza salvare.

---

## Compattatore quantico

### Prerequisiti

1. Sottosistema attivo con tipo **compattatore** (es. codice `Z`)
2. Toggle **Console compattatore** in Runtime Console
3. Livello sottosistema Z &gt; 0 e online (non espulso)
4. Componenti in stiva per le operazioni

### Console

URL kiosk: `/pilot/?screen=compattatore`

- **Energia**: a ogni tick pilota, `accumulatore += livello_Z` (max operativo a soglia **9**)
- **Compressione 2:1**: consuma 2 unità del componente selezionato → 1 unità dell’indice successivo (anello 0↔9)
- **Decompressione 1:2**: consuma 1 unità → 2 unità dell’indice precedente
- **Risonanza**: consuma 1 componente; due slot A/B con probabilità (stesso 35%, adiacenti 20%+20%, distanza 2 10%+10%, anomalia 3%/5%); glitch 2% solo slot A
- **Compattatore Quantico**: **FUORI USO** di default (`compattatore_quantico_abilitato=false` in Runtime Console). Staff lo attiva solo per l'evento.

API console (token pilota):

| Endpoint | Uso |
|----------|-----|
| `GET /api/pilot/compattatore/state/` | Stato energia, stiva, operatività, flag quantico |
| `POST /api/pilot/compattatore/compressione/` | `{ "mattone_id": "uuid" }` |
| `POST /api/pilot/compattatore/decompressione/` | `{ "mattone_id": "uuid" }` |
| `POST /api/pilot/compattatore/risonanza/` | `{ "mattone_id": "uuid" }` |
| `POST /api/pilot/compattatore/quantico/` | `{ "nome_oggetto": "..." }` o `{ "qr_id", "personaggio_id" }` |

---

## Compattatore Quantico — teoria (evento)

> Stato produzione: implementato ma **spento** fino al prossimo evento live. Toggle staff: **Compattatore Quantico** in Runtime Console.

### Concetto

Il giocatore (o l'operatore console) **sacrifica un oggetto** — descritto a testo o identificato da **QR** — che viene **eliminato** dal gioco. Il compattatore non lo ricostruisce: lo **disintegra** e ne estrae materia componente nella **stiva globale nave**.

### Input

| Modalità | Campi | Effetto sull'oggetto |
|----------|-------|----------------------|
| **Testo** | `nome_oggetto` (min. 2 caratteri alfanumerici) | Nessun oggetto fisico rimosso; il nome guida solo l'algoritmo (narrativo / prova) |
| **QR + personaggio** | `qr_id`, `personaggio_id` | L'`Oggetto` collegato al QR viene rimosso dall'inventario del PG ed eliminato |
| **QR senza personaggio** | `qr_id` | Solo nome ricavato dal QR (nessuna eliminazione) |

### Algoritmo computazionale (deterministico)

1. **Normalizzazione**: dal nome si tengono solo lettere A–Z e cifre 0–9, maiuscolo.  
   Es. `Reattore Mk-II` → `REATTOREMKII`
2. **Quantità**: `N = 1 + (SHA256(nome)[0] mod 5)` → da **1 a 5** unità di componente.
3. **Per ogni unità** `i` (0 … N−1):
   - lettera sorgente = `nome[i mod len(nome)]`
   - `indice_componente = (ord(lettera) + digest[i+1] + i) mod 10` (anello 0–9)
   - si aggiunge 1 mattone componente con quell'indice in stiva
4. Stesso nome → stesso risultato (riproducibile per playtest e log).

### Costo energetico

Come le altre operazioni: **9** punti energia accumulata e sottosistema Z operativo.

### Attivazione / disattivazione evento

Il flag **`compattatore_quantico_abilitato`** è su `PilotRuntimeConfig` (default **`false`**). Con flag off:

- API `POST /api/pilot/compattatore/quantico/` risponde **400** («disabilitato»)
- In console pilota il pulsante mostra **«Compattatore Quantico — FUORI USO»**

Per l’evento live:

```bash
# Staff → Pilotaggio → Runtime Console → spunta «Compattatore Quantico»
# oppure PATCH /api/pilot/staff/runtime-config/ { "compattatore_quantico_abilitato": true }
```

Dopo l'evento: **disattivare** il flag per tornare a «FUORI USO» in console.

---

## Tab Stiva nave (giocatore)

Visibile nel menu app se il personaggio ha **`0IN` > 0** (o la statistica configurata in Runtime Console → «Statistica accesso compattatore»).

- Tab **Stiva nave**: inventario globale in sola lettura, stato coppie opposte
- API: `GET /api/pilot/stiva/?personaggio_id=<uuid>` (403 senza statistica)

Per fissare il tab nel menu rapido: icona pin nel drawer laterale.

---

1. Scan QR sottosistema guasto
2. Check **0RI** > 0
3. Minigioco (se configurato sul QR)
4. Se riparazione componenti attiva: **picker in modale QR** — selezione componenti da stiva nave (conteggio per vincolo specifico / a scelta)
5. Ripristino sottosistema online

Senza componenti sufficienti la riparazione **non** si completa.

---

## Annichilamento opposti (regola)

- Per ogni coppia: se **entrambi** i colori hanno quantità > 0 in stiva, `tick_coesistenza` avanza a ogni tick pilota
- Dopo **5 tick** di coesistenza: `n = min(qty_A, qty_B)` annichilato in **un colpo**
- Se una quantità torna a 0, il contatore si azzera

Hook: fine `tick_sessione` → `applica_stiva_tick_se_dovuto()`.

---

## API principali

| Endpoint | Uso |
|----------|-----|
| `GET /api/pilot/stiva/` | Inventario (autenticato) |
| `GET/POST /api/pilot/staff/stiva/` | Staff: lettura / `POST {mattone_id, delta}` |
| `POST /api/pilot/subsystems/qr-repair/` | Esteso con `componenti_scelti[]` |
| `POST /api/pilot/staff/eventi/aggiorna-codici-da-stato/` | Rigenera codici evento |
| `GET /api/pilot/compattatore/state/` | Stato compattatore (console) |
| `POST /api/pilot/compattatore/compressione/` | Compressione 2:1 |
| `POST /api/pilot/compattatore/decompressione/` | Decompressione 1:2 |

---

## Sync edge

Modelli sincronizzabili: `StivaComponenteNave`, `CoppiaColoriComponente`, `StivaCoppiaOppositiStato`, configurazioni sottosistema.

Dopo migrate: eseguire migrate su **master e replica** prima di affidarsi al sync.

`PilotRuntimeConfig` è singleton locale (non sync).

---

## Prossime fasi (roadmap)

Sistema componenti / compattatore **completo** per il live play. Il Quantico resta **spento** (`compattatore_quantico_abilitato=false`) fino all'evento; vedi sezione teoria sopra.
