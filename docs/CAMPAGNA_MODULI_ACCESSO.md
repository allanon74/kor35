# Moduli campagna (accesso feature)

Staff → **Campagne** → tab **Moduli** (tab di default).

Per ogni campagna si imposta OFF / TEST / OPEN sui moduli (Tasks, Pilotaggio, Carte, Scommesse, Social, Negozi, Creazione guidata).

Altri tab dello stesso tool: **Campagne** (CRUD), **Membership**, **Policy catalogo** (SHARED/EXCLUSIVE — non confondere con OFF/TEST/OPEN).

| Modo | Effetto |
|------|---------|
| **OFF** | Nascosto a giocatori e tool staff collegati |
| **TEST** | Solo staff/master (ruolo campagna STAFFER+) e PnG non giocanti |
| **OPEN** | Tutti i PG della campagna |

- Campo DB: `Campagna.moduli_accesso` (JSON). Chiavi assenti → default registry (`personaggi/campagna_moduli.py`).
- **Carte**: bridge bidirezionale con `ConfigurazioneCarteCollezionabili.accesso_modo`.
- FE: `CharacterContext.canAccessModulo` + filtro tool in `StaffDashboard`.
- API missioni: gate su modulo `tasks`.
