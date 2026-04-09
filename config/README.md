## Config di deploy (monorepo)

Questa cartella contiene la configurazione **versionata** dei server, separata dal codice.

### Struttura proposta

- `config/production/`
  - Config del server MASTER (DigitalOcean).
- `config/mirror/`
  - Config del server EDGE/Mirror (Raspberry Pi).

### Note operative

- I workflow di deploy possono copiare questi file nelle destinazioni reali (es. `/etc/apache2/...`, root progetto mirror, ecc.)
  **solo se cambiati**, e poi fare `reload` dei servizi necessari.
- I file multimediali restano gestiti fuori da Git (sync via `rsync`/filesystem), come da regole progetto.

