# Card Studio (MSE-first)

Web app separata staff-only per authoring carte:

- espansioni (`EspansioneCarte`)
- catalogo carte (`CartaCollezionabile`)
- keyword (`KeywordCarta`)
- campi platform (`studio_*`, `mse_*`, `arena_playable_spec`)

## Avvio locale

```bash
npm --prefix apps/card-studio install
npm --prefix apps/card-studio run dev
```

URL dev: `https://localhost:5173/cardeditor/`

## Build

```bash
npm --prefix apps/card-studio run build
```

Output: `apps/card-studio/dist/` (da servire su `/cardeditor/` via nginx).

## API usate

- `/api/personaggi/api/staff/carte/espansioni/`
- `/api/personaggi/api/staff/carte/catalogo/`
- `/api/personaggi/api/staff/carte/keywords/`
- `/api/personaggi/api/staff/carte/platform/gioco/`
- `/api/personaggi/api/staff/carte/platform/templates/`

Auth: sessione Django (`credentials: include`).
