SHELL := /bin/bash

# Profili supportati: dev-home, dev-office, mirror, prod
ENV ?= dev-home
CLEANUP_LEGACY ?= 0
SYNC_SINCE ?=
RUN_MIGRATIONS ?= 0
RUN_PIP_INSTALL ?= 0
RUN_COLLECTSTATIC ?= 0
MAKEMIGRATIONS_APP ?=

.PHONY: help setup env up up-no-build up-no-static down down-volumes logs status collectstatic migrate makemigrations restart restart-fe restart-be sync-db sync-db-full sync-media cleanup-legacy backup-db

help:
	@echo "KOR35 monorepo helper"
	@echo ""
	@echo "Uso:"
	@echo "  make <target> [ENV=dev-home|dev-office|mirror|prod]"
	@echo "  opzionale: CLEANUP_LEGACY=1 (rimuove container legacy kor35_wsl_*)"
	@echo "  opzionale restart-be/restart:"
	@echo "    RUN_MIGRATIONS=1   # esegue migrate dopo restart backend/daphne"
	@echo "    RUN_PIP_INSTALL=1  # esegue pip install -r requirements.txt nel container backend"
	@echo "    RUN_COLLECTSTATIC=1 # esegue collectstatic nel container backend"
	@echo ""
	@echo "Target principali:"
	@echo "  make env ENV=dev-home        # crea/attiva backend/.env.<env>"
	@echo "  make setup                   # prepara runtime + build frontend"
	@echo "  make up                      # avvia stack (con build + collectstatic)"
	@echo "  make up-no-build             # avvio senza rebuild immagini"
	@echo "  make up-no-static            # avvio senza collectstatic"
	@echo "  make migrate                 # esegue migrate nel container backend"
	@echo "  make makemigrations          # crea migrazioni (opzionale: MAKEMIGRATIONS_APP=personaggi)"
	@echo "  make status                  # stato container"
	@echo "  make logs                    # log live (tutti i servizi)"
	@echo "  make down                    # stop stack"
	@echo "  make down-volumes            # stop + rimozione volumi"
	@echo "  make cleanup-legacy          # rimuove vecchi container kor35_wsl_*"
	@echo ""
	@echo "Dopo modifiche al codice (stack già avviato):"
	@echo "  make restart-fe ENV=dev-home # rebuild React + riavvio container nginx (frontend)"
	@echo "  make restart-be ENV=dev-home # riavvia backend + daphne (carica .py aggiornati)"
	@echo "  make restart ENV=dev-home    # restart-fe + restart-be"
	@echo "  make restart ENV=dev-home RUN_MIGRATIONS=1 RUN_PIP_INSTALL=1 RUN_COLLECTSTATIC=1"
	@echo ""
	@echo "Sync:"
	@echo "  make sync-db [SYNC_SINCE=ISO_DATETIME] # pull-only DB (backend container)"
	@echo "  make sync-db-full            # pull-only completo da 1970-01-01T00:00:00Z"
	@echo "  make sync-media              # pull-only media via rsync (vedi scripts/sync_media_pull_wsl_pi_like.sh e .env.sync-media)"
	@echo ""
	@echo "Backup:"
	@echo "  make backup-db ENV=prod      # dump DB su file + rotazione (vedi scripts/backup_db_daily.sh)"

setup:
	./scripts/setup_wsl_pi_like.sh

env:
	./scripts/use_env_backend.sh --env "$(ENV)"

up:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)"

up-no-build:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build

up-no-static:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --skip-collectstatic

down:
	./scripts/down_wsl_pi_like.sh --env "$(ENV)"

down-volumes:
	./scripts/down_wsl_pi_like.sh --env "$(ENV)" --volumes

logs:
	./scripts/logs_wsl_pi_like.sh --env "$(ENV)"

status:
	./scripts/status_wsl_pi_like.sh --env "$(ENV)"

collectstatic:
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build --skip-collectstatic
	cd config/docker && KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py collectstatic --noinput

migrate:
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build --skip-collectstatic
	cd config/docker && KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py migrate --noinput

makemigrations:
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build --skip-collectstatic
	cd config/docker && KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py makemigrations $(MAKEMIGRATIONS_APP)

# Build React → react_build, poi riavvio del servizio nginx (frontend) così gli statici sono serviti freschi.
restart-fe:
	./scripts/setup_wsl_pi_like.sh
	cd config/docker && KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml restart frontend

# Riavvia backend + daphne così Gunicorn/Daphne carica le modifiche ai file Python (bind-mount backend).
restart-be:
	cd config/docker && KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml restart backend daphne
	@if [ "$(RUN_PIP_INSTALL)" = "1" ]; then \
		cd config/docker && KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend sh -lc "python -m pip install -r requirements.txt"; \
	fi
	@if [ "$(RUN_MIGRATIONS)" = "1" ]; then \
		cd config/docker && KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py migrate --noinput; \
	fi
	@if [ "$(RUN_COLLECTSTATIC)" = "1" ]; then \
		cd config/docker && KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py collectstatic --noinput; \
	fi

restart: restart-fe restart-be

sync-db:
	cd config/docker && KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py sync_edge_node --pull-only $(if $(SYNC_SINCE),--since "$(SYNC_SINCE)",)

sync-db-full:
	$(MAKE) sync-db ENV="$(ENV)" SYNC_SINCE="1970-01-01T00:00:00Z"

sync-media:
	./scripts/sync_media_pull_wsl_pi_like.sh

cleanup-legacy:
	./scripts/cleanup_legacy_wsl_stack.sh

backup-db:
	./scripts/backup_db_daily.sh --env "$(ENV)"
