# 08 — Permessi e identità

## Tre livelli identità

| Livello | Modello | Uso |
|---------|---------|-----|
| Account | `User` | Login Django, staff |
| Giocatore platform | `CartePlatformGiocatore` | Arena standalone / bridge |
| Personaggio LARP | `Personaggio` | Collezione in-world, bustine, duello KOR35 |

## Matrice accesso (target)

| Risorsa | Chi |
|---------|-----|
| `CarteGiocoDefinizione` | Master / staff carte |
| `CarteStudioTemplate` | `editor_carte` |
| Catalogo `CartaCollezionabile` | `editor_carte` (write), PG (read se carte abilitate) |
| `CartaPosseduta` | proprietario personaggio |
| `MazzoDuello` | proprietario personaggio |
| `DuelloCarte` | partecipanti |
| Job import MSE | Master + `editor_carte` |

Fase 0: tutto platform staff dietro `IsStaffOrMaster` (come catalogo carte).

## Capability `editor_carte` (da implementare)

Estendere governance campagna:

```python
# esempio futuro in gestione_plot
def user_can_edit_carte(user, campagna) -> bool:
    if user.is_staff:
        return True
    return campagna_has_capability(user, campagna, "editor_carte")
```

Registrare in policy campagna insieme a feature `FEATURE_CARTE_COLLEZIONABILI`.

## Collezione: sempre per personaggio in KOR35

`CartaPosseduta.personaggio` resta FK obbligatoria nel bridge KOR35.

Arena standalone (futuro) potrebbe introdurre `CartaPosseduta` con personaggio «tecnico» per account-only; **non** in Fase 0.

## `external_player_ref`

UUID opzionale su `CartePlatformGiocatore` per federare identità se Arena è su subdomain con auth separata. Non usato finché shared session.

## Privacy

- `arena_playable_spec` non contiene dati personali
- Job exchange loggano `richiesto_da` per audit staff
- Export MSE non include email utente

## Sync e identità

`CartePlatformGiocatore.sync_id` partecipa edge sync. Su replica, stesso personaggio → stesso bridge record dopo pull master.

**Non** usare `id` numerico locale per riferimenti cross-nodo; usare `sync_id` / UUID PK.

## Checklist sicurezza Fase 2 Arena

- [ ] WS autenticato (session o JWT)
- [ ] Azioni duello validate server-side solo
- [ ] Nessun EffectScript eseguito client-side in produzione
- [ ] Rate limit su matchmaking
