Docker configuration matrix (target layout).

Obiettivo: configurazioni condivise + override per ambiente.

Struttura prevista:
- `compose.base.yml` (servizi comuni)
- `compose.prod.yml` (DigitalOcean production + coturn HMAC)
- `compose.mirror.yml` (Raspberry mirror, include Omada + coturn TURN)
- `compose.dev-home.yml` (sviluppo locale casa + coturn)
- `compose.dev-office.yml` (sviluppo locale ufficio + coturn)
- `compose.coturn.yml` (relè TURN WebRTC, incluso dagli overlay LAN e prod)
- `compose.dev-standalone.yml` (db+redis stand-alone legacy)

Compatibilità:
- i file legacy in `config/docker/nginx-docker/` restano come asset di transizione
  (nginx conf, compose storico e runtime dirs).
