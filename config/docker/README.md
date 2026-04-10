Docker configuration matrix (target layout).

Obiettivo: configurazioni condivise + override per ambiente.

Struttura prevista:
- `compose.base.yml` (servizi comuni)
- `compose.prod.yml` (DigitalOcean production)
- `compose.mirror.yml` (Raspberry mirror, include Omada)
- `compose.dev-home.yml` (sviluppo locale casa)
- `compose.dev-office.yml` (sviluppo locale ufficio)

In questa fase iniziale il branch mantiene ancora i compose legacy in `config/docker/nginx-docker/`.
