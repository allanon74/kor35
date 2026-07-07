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

In produzione il deploy CI esegue già `sync_wiki_staff_ops --force` dopo migrate/collectstatic.
Per un aggiornamento manuale:

```bash
make wiki-staff-sync ENV=prod WIKI_STAFF_FORCE=1
```

## Regola per modifiche

Quando modifichi `Makefile`, `docs/MIRROR_PI_NETWORK.md`, target mirror o runbook Docker/sync, aggiorna anche i `.md` in questa cartella (il deploy CI sincronizza prod automaticamente).

## Note carte governance (Fase 1)

- `EspansioneCarte`: `attiva`, `in_vendita` + finestra `vendita_dal`/`vendita_al`, `legale_duello`, `disclaimer_disattiva`.
- `CartaCollezionabile`: `legale_duello`, `bandita`, `ban_reason`.
- Enforcement: bustine acquistabili solo se espansione in vendita; carte di espansioni disattive non compaiono ai giocatori; carte bandite/non legali bloccate nei mazzi duello ma restano valide nel reliquiario.
- Con campagna in `OPEN`, in staff i campi gameplay carta sono bloccati lato API (UI con guardia disabilitata); reliquiario/lore restano editabili.

Vedi `.cursor/rules/wiki-staff-ops.mdc`.
