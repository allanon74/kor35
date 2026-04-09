## Cutover deploy monorepo (DigitalOcean + Raspberry Pi)

Questo documento allinea definitivamente i path server al monorepo `kor35`.

### 1) Secrets GitHub Actions da impostare/aggiornare

#### Production (DigitalOcean)

- `SERVER_PROJECT_PATH` = path clone monorepo (es. `/home/<user>/progetti/kor35`)
- `REPO_PATH_ON_SERVER` = stesso path monorepo (usato dal job frontend)
- `APACHE_SITE_DEST` = destinazione file Apache (opzionale), es. `/etc/apache2/sites-available/kor35.conf`

#### Mirror (Raspberry Pi)

- `MIRROR_MONOREPO_PATH` = `/home/pi/kor35-replica`
- `MIRROR_MONOREPO_REPO_URL` = URL repo `kor35` (SSH o HTTPS)
- `MIRROR_ROOT_PATH` = `/home/pi/kor35-replica`
- `MIRROR_REACT_BUILD_PATH` = `/home/pi/kor35-replica/react_build`

### 2) Preparazione server (una tantum)

#### DigitalOcean

1. Assicurati che il clone sul server punti al repo `kor35`.
2. Verifica presenza cartelle:
   - `<SERVER_PROJECT_PATH>/backend`
   - `<SERVER_PROJECT_PATH>/frontend`

#### Raspberry Pi

1. Porta il mirror sul path standard:
   - repo in `/home/pi/kor35-replica`
2. Verifica:
   - `/home/pi/kor35-replica/backend`
   - `/home/pi/kor35-replica/frontend`
   - `/home/pi/kor35-replica/docker-compose.yml`

### 3) Config versionata in `config/`

- Apache production: `config/production/apache/kor35.conf` (se usato)
- Mirror compose/nginx: `config/mirror/...`

Il workflow backend mirror aggiorna automaticamente `docker-compose.yml` da
`config/mirror/docker-compose.yml` se presente e modificato.

### 4) Verifica post-cutover

1. Lancia `workflow_dispatch` su `main` con `run_migrations=true`.
2. Controlla esito job:
   - `Production backend deploy`
   - `Production frontend deploy`
   - `Mirror Raspberry backend deploy`
   - `Mirror Raspberry frontend deploy`
3. Verifica healthcheck production/mirror.

### 5) Rollback rapido

Se serve rollback applicativo, rilancia workflow con input `ref` impostato a un tag stabile
(es. `pre-monorepo-2026-04-09`) e `run_migrations=false` se non vuoi toccare schema DB.
