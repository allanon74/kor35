# 10 — Parità MSE e sistema template (Sette Elegie)

Piano operativo per portare Card Studio a un livello **omologo** a Magic Set Editor
(clean-room, senza copiare codice GPL) e per rendere sostenibile la creazione di
**giochi**, **template** e **set** — con priorità a *Cronache delle Sette Elegie*.

## Stato attuale (baseline)

| Area MSE | In KOR35 oggi | Gap |
|----------|---------------|-----|
| `.mse-game` (campi, choice, keyword) | `CarteGiocoDefinizione.meta.mse_game_spec` + bootstrap KOR35 | Editor visuale campi gioco assente |
| `.mse-style` (layout, script, asset) | `CarteStudioTemplate` + import zip + preview layer | Script MSE subset; no mask/shadow compositing |
| `.mse-set` (carte + styling) | `EspansioneCarte` + `CartaCollezionabile.mse_campi` | Export/import set incompleto |
| Symbol font | Package `KOR35 Aure` (7 aure) | No editor glyph; font TTF MSE non web |
| Styling fields | `show_stats` / `show_lore` | UI styling tab base |
| Include / package refs | Risoluzione include game stub | Absolute includes / multi-package incompleti |
| Keyword expand | Keyword DB + effect script | Non equivalente a MSE `expand` |
| Export stampa | PNG 300 dpi (pHYs) da Card Studio | PDF foglio / bleed / cut marks |

**Template Sette Elegie v3.1** (`kor35-standard`): cornici per aura, visibilità per tipo
(PG/OGG/LUO/EVT), art placeholder per tipo, label FOR/ROB/INI, symbol font aure.
Seed demo: **29 carte**.

```bash
make bootstrap-kor35-mse-template ENV=dev-office CAMPAGNA_SLUG=kor35
make seed-carte-esempio ENV=dev-office CAMPAGNA_SLUG=kor35 CARTE_ESEMPIO_FORCE=1
make card-editor-build ENV=dev-office && make restart-fe ENV=dev-office
```

---

## Obiettivo prodotto

Un **MSE-compatible Studio** web, Docker-first, dove lo staff può:

1. Definire un **gioco** (campi, choice colorate, keyword modes).
2. Creare/importare **template** (stylesheet) legati al gioco.
3. Gestire **set/espansioni** con template default.
4. Editare carte con **preview live** fedele al template.
5. Esportare/importare subset MSE per collaborazione / stampa.

Per Sette Elegie: un solo gioco `kor35`, più template (standard, full-art, promo)
e set demo + canon.

---

## Fasi

### Fase A — Fondamenta Sette Elegie (completamento rapido)

**Scopo:** playtest e stampa leggibili senza dipendere da Magic styles.

- [x] Template v3.1 per-aura + visibilità tipo
- [x] Symbol font 7 aure
- [x] Seed demo 29 carte (7 aure × tipi)
- [x] Bootstrap crea gioco/template/set se mancanti
- [x] Asset art placeholder per tipo (PG/OGG/LUO/EVT)
- [x] Export PNG 300 dpi stabile da Card Studio (scale da `card dpi` + pHYs)
- [x] Wiki staff: «Come creare una carta Sette Elegie»
  (`docs/wiki/staff/card-studio-sette-elegie.md` → slug `staff-card-studio-sette-elegie`)

**Criterio di fatto:** da DB vuoto, un comando bootstrap+seed apre Card Studio con
carte preview corrette (cornice MAR ≠ TEC, LUO senza aura/stats); export PNG 300 dpi
scaricabile dalla preview.

### Fase B — Template System (authoring)

**Scopo:** creare template senza scrivere ZIP a mano.

1. **Template Builder UI** (staff):
   - canvas carta (375×523 default) con layer list
   - proprietà MSE-like: box, font, `visible` script, `image` script, z-index
   - upload asset PNG → `mse_extracted_root`
   - save → `layout_spec.mse_v1` + package zip scaricabile
2. **Game Field Editor**:
   - CRUD campi su `mse_game_spec` (text, choice, image, package choice)
   - choice colors cardlist
   - mapping catalogo KOR35 (`tipo`/`energia`/…)
3. **Set defaults panel** sempre visibile (già avviato): gioco + stylesheet default
4. **Validazione**: dry-run parse style ↔ preview; test regressione LWW non tocca template

**API da estendere:**

| Endpoint | Uso |
|----------|-----|
| `POST …/templates/` | Crea template vuoto + schema |
| `POST …/templates/{id}/assets/` | Upload immagine layer |
| `PATCH …/templates/{id}/layout/` | Salva `mse_v1` |
| `POST …/gioco/{id}/fields/` | Aggiorna game spec |
| `POST …/templates/{id}/export-mse-style/` | Download `.mse-style.zip` |

### Fase C — Parità script / render (omologia MSE)

Clean-room, priorità a ciò che usano Sette Elegie e Magic importati:

| Feature | Priorità | Note |
|---------|----------|------|
| `if/then/else` annidati + `=` | Alta | già in corso in `scriptEngine` |
| `and/or/not`, confronti | Alta | |
| `card.*` / `styling.*` / `set.*` | Alta | alias catalogo |
| `symbol font` per layer | Alta | |
| `default_image` / `forward` stub → reale | Media | |
| mask / soft mask | Media | canvas compositing |
| drop shadow | Bassa | CSS filter ok per web |
| keyword `expand` MSE | Media | bridge a KeywordCarta |
| include file resolution | Alta | già per game Magic |
| `@font-face` da package font | Media | subset WOFF |

**Non obiettivo:** clonare l’intero runtime C++ MSE. Obiettivo: preview e stampa
**sufficientemente fedeli** per i template che pubblichiamo.

### Fase D — Import / export set

1. Import `.mse-set` → espansione + carte (`mse_campi` round-trip)
2. Export set KOR35 → zip MSE-compatible (game + style ref + cards)
3. Job asincroni (`CartePlatformExchangeJob`) con log e retry
4. Media via path relativi + `make sync-media` (già architettura Edge)

### Fase E — Multi-template e varianti Sette Elegie

- Template `kor35-standard`, `kor35-fullart`, `kor35-token`
- Override per-carta (`studio_template`)
- Styling fields per set (show lore, foil frame)
- Catalogo asset ufficiali (cornici, gemme aura) in repo o media master

---

## Architettura proposta (authoring)

```
Card Studio UI
  ├─ Game Editor ──► CarteGiocoDefinizione.meta.mse_game_spec
  ├─ Template Builder ──► CarteStudioTemplate.layout_spec.mse_v1 + assets
  ├─ Set Manager ──► EspansioneCarte + default_studio_template
  └─ Card Editor ──► CartaCollezionabile + mse_campi + preview resolveLayers
         │
         ▼
   scriptEngine (subset) + symbolFonts + PNG export
```

Registry sync: i template **non** usano ID auto-increment come chiave di sync;
restano UUID + `updated_at` LWW come il resto della piattaforma.

---

## Priorità Sette Elegie (ordine consigliato)

1. Stabilizzare preview v3 + seed 29 (questa PR)
2. Export PNG stampa + guida staff wiki
3. Template Builder minimo (layer list + upload + save)
4. Script parity per script usati nei nostri style
5. Secondo template (full-art personaggio)
6. Import/export set MSE subset

---

## Metriche di successo

- Tempo «DB vuoto → carta stampabile»: ≤ 2 comandi Make
- Preview Card Studio = export PNG (pixel-diff tolleranza bassa)
- Zero regressioni Magic import (casting cost / symbols) nei test
- Staff crea un nuovo template Sette Elegie senza toccare Python

## Riferimenti

- `docs/card-platform/07-mse-mapping.md`
- `docs/card-platform/03-card-studio-roadmap.md`
- `docs/card-platform/09-kor35-mse-template-prod-runbook.md`
- `config/docker/SYNC.md` (media / ruoli nodo)
- `.cursor/rules/edge-sync.mdc` (se i modelli template entrano nel sync)
