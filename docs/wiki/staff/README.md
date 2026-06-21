# Wiki staff — sorgenti versionate

Pagine **solo staff** nella Wiki KOR, sincronizzate nel DB (`PaginaRegolamento`).

## File

| File | Ruolo |
|------|--------|
| `manifest.json` | Slug, titoli, ordine menu, elenco pagine |
| `make-comandi.md` | Tutti i comandi `make` |
| `mirror-pi.md` | Procedure mirror Raspberry Pi |

## Aggiornare la Wiki

```bash
make wiki-staff-sync ENV=dev-home
# oppure con sovrascrittura esplicita:
make wiki-staff-sync ENV=dev-home WIKI_STAFF_FORCE=1
```

In produzione (dopo deploy):

```bash
make wiki-staff-sync ENV=prod WIKI_STAFF_FORCE=1
```

## Regola per modifiche

Quando modifichi `Makefile`, `docs/MIRROR_PI_NETWORK.md`, target mirror o runbook Docker/sync, aggiorna anche i `.md` in questa cartella e lancia `make wiki-staff-sync`.

Vedi `.cursor/rules/wiki-staff-ops.mdc`.
