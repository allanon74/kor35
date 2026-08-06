# Moduli campagna (accesso feature)

Staff → **Campagne** → tab **Moduli** (tab di default).

Per ogni campagna si imposta OFF / TEST / OPEN sui moduli (Tasks, Pilotaggio, Carte, Scommesse, Social, Negozi, Creazione guidata, Conto di deposito).

Altri tab dello stesso tool: **Campagne** (CRUD), **Membership**, **Policy catalogo** (SHARED/EXCLUSIVE — non confondere con OFF/TEST/OPEN).

| Modo | Giocatori | Staff / tool collegati |
|------|-----------|------------------------|
| **OFF** | Nascosto, API 403 | Tool staff nascosto, API staff 403 |
| **TEST** | Solo staff/master (ruolo campagna STAFFER+) e PnG non giocanti | Accessibile (serve al collaudo) |
| **OPEN** | Tutti i PG della campagna | Accessibile |

- Campo DB: `Campagna.moduli_accesso` (JSON). Chiavi assenti → default registry (`personaggi/campagna_moduli.py`).
- **Carte**: bridge bidirezionale con `ConfigurazioneCarteCollezionabili.accesso_modo`.
- API campagne: `moduli_accesso` = mappa effettiva (default + bridge), `moduli_accesso_raw` = solo override espliciti, `moduli_accesso_registry` = registry con i default.

## Scrittura e ripristino default

`PATCH /api/personaggi/api/staff/campagne/<id>/` con `{"moduli_accesso": {"tasks": "TEST"}}` (merge: aggiorna solo le chiavi passate).

Per rimuovere un override e tornare al default del registry si passa `"DEFAULT"`, `""` o `null`:

```json
{"moduli_accesso": {"tasks": "DEFAULT"}}
```

Nel tab Moduli lo stesso effetto si ottiene con il pulsante **Ripristina default** (visibile solo quando esiste un override). Per `carte`, il ripristino riporta la lettura al bridge con la config Carte collezionabili.

## Gate lato backend

Helper in `personaggi/campagna_moduli.py`:

| Helper | Uso |
|---|---|
| `personaggio_puo_accedere_modulo(pg, key, user=)` | check booleano per PG |
| `modulo_accesso_error(pg, key, user=)` | messaggio di rifiuto o `None` |
| `modulo_gate_response(pg, key, user=, error_key=)` | `Response` 403 pronta per le view DRF |
| `assert_personaggio_puo_accedere_modulo(...)` | variante che alza `ValidationError` |
| `user_puo_accedere_modulo(user, campagna, key)` | tool senza personaggio (wizard, console staff) |
| `ModuloStaffGateMixin` (`modulo_key = ...`) | ViewSet/APIView staff: 403 se il modulo è OFF |
| `staff_tool_abilitato(campagna, tool_id)` | visibilità tool nella dashboard staff |

Endpoint già protetti:

| Modulo | Punto di gate |
|---|---|
| `tasks` | `MissioneViewSet` (mixin staff) + `mie` / `assegna-risoluzione` |
| `pilotaggio` | `PilotQrLoginView`, `subsystems/qr-action|qr-repair|qr-recharge`, `pilot/stiva` |
| `carte` | `carte_collezionabili_service.personaggio_puo_accedere_carte` |
| `scommesse` | `_personaggio_or_error` (tutte le view giocatore) + viewset/config staff |
| `social` | `gate_modulo_social` in post/story/gruppi/profili/notifiche |
| `negozi` | `_get_pg` (tutte le view giocatore) + viewset staff |
| `creazione_guidata` | `_resolve_active_flusso` / `creazione_guidata_stato` |

Se una campagna non è risolvibile dalla richiesta, il gate staff non blocca (setup minimali e test restano funzionanti).

## Gate lato frontend

- `CharacterContext.canAccessModulo(key)` — considera ruolo campagna, staff Django, superuser e **PnG non giocante** del personaggio selezionato (allineato al backend).
- `StaffDashboard` filtra i tool con `staffToolModuloEnabled` (nasconde solo OFF).
- `MainPage` nasconde le tab giocatore con `requiresModulo`.
- Registry e helper condivisi: `frontend/src/lib/campagnaModuli.js` (allineato a `campagna_moduli.py`).

## Test

```bash
docker compose -f compose.base.yml -f compose.dev-home.yml exec -T backend \
  python manage.py test personaggi.tests_campagna_moduli -v 2 --keepdb
```
