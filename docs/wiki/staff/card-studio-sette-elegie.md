# Card Studio — creare una carta Sette Elegie

Guida operativa per lo staff: template **Sette Elegie Standard** (`kor35-standard`),
mazzo demo e export PNG stampabile da **Card Studio** (`/cardeditor/`).

Documentazione tecnica: `docs/card-platform/10-mse-parity-template-system.md`,
runbook prod `docs/card-platform/09-kor35-mse-template-prod-runbook.md`.

---

## Prerequisiti

- Stack Docker avviato sul profilo in uso (`dev-home`, `dev-office`, `mirror`, `prod`).
- Campagna con slug noto (di solito `kor35`).
- Utente staff con permessi editor carte.

---

## 1. Bootstrap template + mazzo demo

Da root monorepo (Docker-first):

```bash
make bootstrap-kor35-mse-template ENV=dev-office CAMPAGNA_SLUG=kor35
```

Cosa fa:

- crea/aggiorna il **gioco** `kor35` e il template `kor35-standard` (v3.2);
- collega le espansioni al gioco;
- con `--seed-demo` (già nel Make) crea/aggiorna **29 carte** demo
  (12 PG, 6 OGG, 8 EVT, 3 LUO; 7 aure).

Solo seed senza ri-generare lo style:

```bash
make seed-carte-esempio ENV=dev-office CAMPAGNA_SLUG=kor35 CARTE_ESEMPIO_FORCE=1
```

Dopo modifiche a Card Studio frontend:

```bash
make card-editor-build ENV=dev-office && make restart-fe ENV=dev-office
```

---

## 2. Aprire Card Studio

1. Vai a `/cardeditor/` (stesso host Nginx del profilo: es. `http://localhost:8081/cardeditor/` in office).
2. Seleziona campagna **kor35** e gioco **Cronache delle Sette Elegie** (slug `kor35`).
3. Tab **Cards**: scegli il set demo (espansione seed) e una carta dall’elenco.

Criterio di ok preview:

- cornice **MAR ≠ TEC ≠ …** (colori aura diversi);
- **LUO** senza simbolo energia e senza FOR/ROB/INI;
- **PG** con badge FOR / ROB / INI;
- art placeholder colorato per tipo se manca l’immagine (PG blu, OGG ambra, LUO verde, EVT rosa).

---

## 3. Creare una nuova carta

1. Nel set corretto, crea/duplica una carta (codice univoco, es. `SE-PG-MAR-01`).
2. Compila i campi MSE / catalogo:

| Campo | Valori tipici |
|-------|----------------|
| `type` / tipo | `PG`, `OGG`, `LUO`, `EVT` |
| `energy` / energia | `MAR` `TEC` `INN` `MAG` `SAC` `PSI` `ARC` (non usata su LUO) |
| `rarity` / rarità | `COM` `NC` `RAR` `EPI` `LEG` `UNI` |
| `name` / nome | titolo sulla title bar |
| `rules` / regole | testo box regole |
| `attack` / `health` / `initiative` | solo PG (FOR / ROB / INI) |
| `image` | path media o lascia vuoto → placeholder per tipo |

3. Controlla la **Card preview** a destra: i layer seguono lo stylesheet MSE del template.
4. Salva la carta (API catalogo KOR35 — stessa `CartaCollezionabile`).

---

## 4. Export PNG 300 dpi

1. Con preview MSE attiva, clicca **PNG 300dpi**.
2. Il file ha pixel = layout carta × (`targetDpi` / `card dpi`); a 300→300 resta **375×523**.
3. Il PNG include metadato **pHYs** a 300 dpi (per software di stampa).
4. Messaggio di stato tipico: `PNG esportato a 300 dpi (375×523px)`.

Non usare URL assoluti per le immagini in produzione: path relativi sotto `/media/…`
(Nginx instrada master o edge).

---

## 5. Tipi e aure (riferimento rapido)

| Tipo | Label UI | Note layout |
|------|----------|-------------|
| PG | Personaggio | Stats FOR/ROB/INI, aura |
| OGG | Oggetto | Aura, no stats PG |
| EVT | Evento | Aura, no stats PG |
| LUO | Luogo | Cornice terra, **no** aura/stats |

Aure: Marziale, Tecnologica, Innata, Magica, Sacra, Psionica, Arcana.

---

## 6. Sync e ambienti

- Template e carte con `sync_id` seguono LWW edge sync come gli altri modelli sync.
- Dopo bootstrap su **prod**, le replica (`dev-office`, mirror) ricevono i dati con `make sync-db`.
- Media (art custom) con `make sync-media` / rsync — non nel JSON sync.
- Pubblica la guida in Wiki: `make wiki-staff-sync ENV=dev-office WIKI_STAFF_FORCE=1`.

---

## Troubleshooting

| Sintomo | Azione |
|---------|--------|
| Preview vuota / stile Magic | riesegui `bootstrap-kor35-mse-template` sulla campagna |
| 0 carte / 0 template | stesso bootstrap + seed; verifica `CAMPAGNA_SLUG` |
| Export PNG fallisce | serve stylesheet MSE importato sul template attivo |
| Art sempre neutra / simboli `{2}` non renderizzati | template non aggiornato (serve v3.2+): rifai bootstrap |
