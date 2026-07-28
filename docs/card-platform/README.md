# Card Platform — panoramica

KOR35 evolve verso una **piattaforma carte in tre layer**, senza big-bang:

| Layer | Nome codice | Ruolo |
|-------|-------------|--------|
| **Editor / stampa** | Card Studio | Creazione set, template, export (ispirato MSE) |
| **Gioco web** | Card Arena | Collezione, mazzi, partite (ispirato GCCG) |
| **Integrazione LARP** | KOR35 Bridge | Personaggio, economia in-game, permessi campagna |

## Strategia per fasi

1. **Fase 0 (questa PR)** — Schema DB + contratti JSON + API staff minime. Gli editor attuali (`CarteCollezionabiliManager`, duello in-app) continuano a funzionare.
2. **Fase 1** — Card Studio MVP (`/cardeditor` o sotto-app React).
3. **Fase 2** — Card Arena MVP (client duello standalone).
4. **Fase 3** — Bridge KOR35 (SSO personaggio, bustine, QR).
5. **Fase 4** — Import/export MSE subset, economia avanzata.

## Principio guida

> **Un solo catalogo dati.** `CartaCollezionabile`, `EspansioneCarte`, `CartaPosseduta` restano la fonte di verità. Card Studio e Card Arena leggono/scrivono tramite contratti versionati, non tabelle parallele.

## Documenti

| File | Contenuto |
|------|-----------|
| [01-architettura.md](./01-architettura.md) | Diagrammi, repo future, confini |
| [02-database-alignment.md](./02-database-alignment.md) | Modelli Django, mapping campi |
| [03-card-studio-roadmap.md](./03-card-studio-roadmap.md) | Implementazione Card Studio |
| [04-card-arena-roadmap.md](./04-card-arena-roadmap.md) | Implementazione Card Arena |
| [05-kor35-bridge.md](./05-kor35-bridge.md) | Integrazione personaggio / campagna |
| [06-contratti-json.md](./06-contratti-json.md) | Schemi `*_spec_v1` |
| [07-mse-mapping.md](./07-mse-mapping.md) | MSE2 ↔ KOR35 |
| [08-permessi-identita.md](./08-permessi-identita.md) | User, PlayerProfile, Personaggio |
| [09-kor35-mse-template-prod-runbook.md](./09-kor35-mse-template-prod-runbook.md) | Template KOR35 + allineamento stylesheet prod |

## Codice backend introdotto

- `backend/personaggi/carte_platform_models.py` — definizione gioco, template, ruleset, giocatore, job
- `backend/personaggi/carte_platform_specs.py` — versioni contratti + `build_playable_spec_from_carta`
- `backend/personaggi/views_carte_platform.py` — API staff `/api/staff/carte/platform/…`
- Migrazione `0243_carte_platform_bridge.py`

## Comandi operativi

```bash
# Dopo deploy: migrate su tutti i nodi (master + replica)
make migrate ENV=dev-home

# Bootstrap definizione gioco per campagna (API)
POST /api/staff/carte/platform/gioco/{id}/bootstrap/

# Rigenera playable spec su tutte le carte (job MVP)
POST /api/staff/carte/platform/jobs/  # tipo=export_playable
POST /api/staff/carte/platform/jobs/{id}/esegui-export-playable/

# Template MSE KOR35 + refresh layout template importati
make bootstrap-kor35-mse-template-dry-run ENV=dev-office CAMPAGNA_SLUG=kor35
make bootstrap-kor35-mse-template ENV=prod CAMPAGNA_SLUG=kor35
# Runbook: docs/card-platform/09-kor35-mse-template-prod-runbook.md
```

## Riferimenti esterni (solo studio, no copy GPL)

- `external/MagicSetEditor2` — formato `.mse-set` / scripting
- `external/gccg` — lobby, collezione, tavolo (riferimento architetturale)
