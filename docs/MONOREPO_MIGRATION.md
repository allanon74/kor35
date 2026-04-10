# Migrazione Monorepo Docker (`branch: docker`)

Obiettivo: convergere verso un solo repository `kor35` con struttura coerente tra
sviluppo, mirror e produzione.

## Struttura target

- `backend/` codice Django
- `frontend/` codice React/Vite (importato da `kor35-app`)
- `config/docker/` compose base + override ambiente
- `scripts/` tooling operativo (up/down/logs/sync/deploy helper)
- `docs/` runbook e checklist

## Stato corrente

- frontend importato in `frontend/` tramite `git subtree`
- cartelle target inizializzate:
  - `backend/`
  - `config/docker/`
- compatibilità temporanea mantenuta:
  - backend migrato in `backend/` (con riallineamento script in corso)
  - compose legacy in `config/docker/nginx-docker/`
  - script WSL Pi-like aggiornato per usare `frontend/` se presente

## Passi successivi

1. Spostare backend in `backend/` con layer compatibilità minimo.
2. Creare `config/docker/compose.base.yml` + override:
   - `compose.prod.yml`
   - `compose.mirror.yml`
   - `compose.dev-home.yml`
   - `compose.dev-office.yml`
3. Aggiornare script e workflow per usare la nuova struttura.
4. Validare deploy su server secondario DO.
5. Cutover finale su `main` dopo test completi.

## Guard rail

- Deploy remoto consentito solo da `main`.
- Sul branch `docker` sono permessi solo build/test locali e CI non distruttiva.
