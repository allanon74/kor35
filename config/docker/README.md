Docker configuration matrix (target layout).

Obiettivo: configurazioni condivise + override per ambiente.

Struttura prevista:
- `compose.base.yml` (servizi comuni)
- `compose.prod.yml` (DigitalOcean production)
- `compose.mirror.yml` (Raspberry mirror, include Omada)
- `compose.dev-home.yml` (sviluppo locale casa)
- `compose.dev-office.yml` (sviluppo locale ufficio)
- `compose.dev-standalone.yml` (db+redis stand-alone legacy)

Compatibilità:
- i file legacy in `config/docker/nginx-docker/` restano come asset di transizione
  (nginx conf, compose storico e runtime dirs).
