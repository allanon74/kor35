# Replica Ambiente Dev su Nuova Macchina (WSL)

Questa checklist e' pensata per ricreare rapidamente un ambiente KOR35 su un nuovo laptop, usando il profilo `dev-home`.

## 0) Prerequisito iniziale (manuale)

- Installa WSL2 + Ubuntu.
- Apri una shell Ubuntu WSL con un utente non-root (es. `django`).

## 1) Clona il repository

```bash
mkdir -p /home/django/progetti
cd /home/django/progetti
git clone https://github.com/allanon74/kor35.git
cd kor35
```

## 2) Bootstrap host (APT + Docker + tool base)

Script consigliato:

```bash
cd /home/django/progetti/kor35
sudo ./scripts/bootstrap_wsl_dev_host.sh
```

Opzioni utili:

```bash
# se non vuoi installare Node/npm sul nuovo host
sudo ./scripts/bootstrap_wsl_dev_host.sh --skip-node

# se vuoi anche GitHub CLI
sudo ./scripts/bootstrap_wsl_dev_host.sh --install-gh
```

Dopo il bootstrap:

- chiudi e riapri WSL (oppure esegui `newgrp docker`) per applicare il gruppo `docker`;
- verifica:

```bash
docker --version
docker compose version
make --version
node --version
npm --version
```

## 3) Crea il profilo ambiente backend

```bash
cd /home/django/progetti/kor35
make env ENV=dev-home
```

Questo crea/allinea `backend/.env.dev-home` e copia il profilo attivo in `backend/.env`.

## 4) Copia file locali dalla vecchia macchina

### 4.1 File obbligatori per `dev-home`

1) **Sorgente**: vecchia macchina `backend/.env.dev-home`  
2) **Destinazione**: nuova macchina `backend/.env.dev-home`

Contiene almeno:
- `EDGE_SYNC_URL`
- `EDGE_SYNC_TOKEN`
- `PILOT_CONSOLE_ENABLED=true` (se questa macchina deve esporre la console `/pilot/`)
- eventuali variabili locali aggiuntive necessarie al tuo setup.

### 4.2 File consigliati (se usi sync media)

1) **Sorgente**: vecchia macchina `.env.sync-media`  
2) **Destinazione**: nuova macchina `.env.sync-media`

Contiene tipicamente:
- `WSL_PI_REMOTE_SSH_USER`
- `WSL_PI_REMOTE_SSH_HOST`
- `WSL_PI_REMOTE_SSH_PORT`
- `WSL_PI_REMOTE_SSH_IDENTITY`
- `WSL_PI_REMOTE_MEDIA_DIR`

### 4.3 Chiavi SSH da copiare (se usate dalla sync)

- Copia la chiave privata referenziata da `WSL_PI_REMOTE_SSH_IDENTITY` in `~/.ssh/` sulla nuova macchina.
- Imposta i permessi:

```bash
chmod 600 ~/.ssh/<nome-chiave>
```

- Verifica accesso SSH una volta:

```bash
ssh -i ~/.ssh/<nome-chiave> <user>@<host> -p <porta>
```

## 5) Setup runtime progetto e avvio stack

```bash
cd /home/django/progetti/kor35
make setup
make up ENV=dev-home
```

Se hai conflitti con vecchi container legacy:

```bash
make up ENV=dev-home CLEANUP_LEGACY=1
```

## 6) Verifiche finali

```bash
make status ENV=dev-home
make logs ENV=dev-home
```

URL frontend locale:
- `http://127.0.0.1:8080`

## 7) Comandi rapidi quotidiani

```bash
make restart-fe ENV=dev-home
make restart-be ENV=dev-home
make restart ENV=dev-home
make down ENV=dev-home
```

## 8) Clone "veloce" del profilo su altre macchine

Per replicare il setup su un altro laptop:
1. ripeti i punti 1 e 2;
2. copia `backend/.env.dev-home` (e `.env.sync-media` se necessario);
3. esegui `make setup`;
4. esegui `make up ENV=dev-home`.
