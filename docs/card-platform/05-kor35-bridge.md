# 05 — KOR35 Bridge

## Scopo

Permettere a KOR35 di **invocare** Card Studio e Card Arena con identità **personaggio** (non solo account utente), economia in-game (bustine, crediti) e permessi campagna.

## Flussi

### Apertura Card Studio da staff dashboard

```
Staff (editor_carte) → /cardeditor?campagna={slug}
  → session cookie KOR35
  → API staff catalogo (campagna da header/session)
```

### Apertura Card Arena da scheda personaggio

```
PG → pulsante «Duello Arena»
  → /cardarena?personaggio={uuid}&campagna={slug}
  → backend risolve CartePlatformGiocatore per personaggio
  → collezione = CartaPosseduta.filter(personaggio=…)
```

## Modello identità

```
User (account Django)
  └── Personaggio (PG in campagna)
        ├── CartaPosseduta[] 
        ├── MazzoDuello[]
        └── CartePlatformGiocatore (1:1, bridge Arena)
```

Creazione lazy `CartePlatformGiocatore` al primo accesso Arena:

```python
def get_or_create_platform_giocatore(personaggio):
    gioco = CarteGiocoDefinizione.objects.get(campagna=personaggio.campagna)
    return CartePlatformGiocatore.objects.get_or_create(
        personaggio=personaggio,
        defaults={
            "campagna": personaggio.campagna,
            "gioco_definizione": gioco,
            "user": personaggio.proprietario,
            "display_name": personaggio.nome,
        },
    )
```

## Economia bustine

**Resta in KOR35** fino a Fase 4:

- `BustinaCarte`, `apri_bustina`, `ConfigurazioneCarteCollezionabili`
- Card Arena **legge** collezione risultante, non gestisce acquisti

Opzionale Fase 3: evento webhook `bustina_aperta` → invalida cache collezione Arena.

## Permessi

| Azione | Permesso |
|--------|----------|
| Edit catalogo / Studio | Staff + capability `editor_carte` |
| Deck / duello | PG con `accesso_modo` carte OPEN o TEST |
| Config game platform | Master campagna |

Implementazione `editor_carte`: estendere `CampagnaFeaturePolicy` o ruoli esistenti in `gestione_plot` — **non ancora implementato in Fase 0**.

## SSO / token cross-app

Fase 3 opzioni:

1. **Shared session** — stesso dominio, cookie session (più semplice)
2. **JWT breve** — `POST /api/carte/platform/session-token/` con `personaggio_id` → Arena usa header `Authorization`

Preferenza iniziale: shared session (stesso nginx, path `/cardarena`).

## Feature flags

Su `CarteGiocoDefinizione`:

- `studio_abilitato` — mostra link Card Studio in staff
- `arena_abilitata` — mostra link Arena in scheda PG

## Sync edge

Personaggio e carte possedute già sincronizzano. `CartePlatformGiocatore` segue sync campagna. In evento offline mirror: Arena sul Pi usa stesso DB replica.

## Nginx

```nginx
location /cardeditor/ {
    alias /var/www/card-studio/;
    try_files $uri $uri/ /cardeditor/index.html;
}
location /cardarena/ {
    alias /var/www/card-arena/;
    try_files $uri $uri/ /cardarena/index.html;
}
```

API invariata su `/api/`.

## Checklist integrazione Fase 3

- [ ] Helper `get_or_create_platform_giocatore`
- [ ] Link UI staff + personaggio
- [ ] Flag `studio_abilitato` / `arena_abilitata` rispettati
- [ ] Test permessi campagna
- [ ] Wiki staff aggiornata
