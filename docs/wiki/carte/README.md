# Wiki regolamento carte (Cronache delle Sette Elegie)

Sorgenti versionate per la sezione Wiki **Gioco carte**.

## File

| File | Ruolo | Visibilità Wiki |
|------|--------|-----------------|
| `manifest.json` | Sezione parent + elenco pagine | — |
| `regolamento.md` | Bozza regolamento per giocatori | Tutti (se `accesso_modo` OPEN) o solo staff |
| `keywords-staff.md` | Guida master: composizione keyword, duello, roadmap effetti | **Solo master+** (`visibile_solo_staff`) |

Slug pagine:

- Parent: `gioco-carte`
- Regolamento PG: `carte-collezionabili-regolamento`
- Guida keyword staff: `carte-keywords-staff`

## Sincronizzazione nel database

```bash
make wiki-carte-sync ENV=dev-home
# Sovrascrive pagine già presenti (dopo edit manuali in Wiki):
make wiki-carte-sync ENV=dev-home WIKI_CARTE_FORCE=1
```

Equivalente Docker:

```bash
cd config/docker
docker compose -f compose.base.yml -f compose.dev-home.yml exec -T backend \
  python manage.py sync_wiki_carte_regolamento --force
```

Da **Dashboard staff → Carte collezionabili → Config** è disponibile anche il pulsante *Sincronizza da repo*.

## Visibilità Wiki

| Pagina | Chi la vede |
|--------|-------------|
| `carte-keywords-staff` | Solo master / head master / admin (flag `visibile_solo_staff`) |
| `carte-collezionabili-regolamento` | Staff sempre; giocatori solo se `accesso_modo` = `OPEN` |
| Sezione `gioco-carte` | Come regolamento (filtro `carte_wiki_access`) |

| `accesso_modo` carte | Chi vede il regolamento in Wiki |
|----------------------|----------------------------------|
| `OFF` / `TEST` | Solo staff campagna |
| `OPEN` | Tutti i giocatori (+ regolamento) |

La bozza resta **modificabile dalla Wiki** dopo il sync; con `--force` / `WIKI_CARTE_FORCE=1` il contenuto viene sovrascritto dalle sorgenti repo.

## Keyword parametrizzate

Gestione operativa: **staff → Carte → Keywords** e guida completa in `keywords-staff.md` (sync Wiki).

Placeholder nel **nome** e nei testi regola: `[X]`, `[Y]`, … (lettere maiuscole).

Esempio **Mutazione**:

| Campo | Valore |
|-------|--------|
| Codice | `MUTAZIONE` |
| Nome | `Mutazione [X]` |
| Testo regola | `Quando questo personaggio si esaurisce, sostituiscilo con una carta fino a costo [X].` |

Su una carta con testo `… Mutazione 0 …` l'app evidenzia **Mutazione 0** e al tap mostra *…costo 0.*

Mount Docker: `docs/wiki/carte` → `/app/wiki_carte_content` (vedi `compose.base.yml`).
