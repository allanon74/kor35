SHELL := /bin/bash

# Profili supportati: dev-home, dev-office, mirror, prod
ENV ?= dev-home
CLEANUP_LEGACY ?= 0
SYNC_SINCE ?=
RUN_MIGRATIONS ?= 0
RUN_PIP_INSTALL ?= 0
RUN_COLLECTSTATIC ?= 0
RECREATE_FRONTEND ?= 0
ALLOW_DB_REINIT ?= 0
MAKEMIGRATIONS_APP ?=
COMPOSE_PROJECT_NAME_ARG = $(if $(filter mirror,$(ENV)),COMPOSE_PROJECT_NAME=kor35-replica,$(if $(filter prod,$(ENV)),COMPOSE_PROJECT_NAME=kor35-prod,))

.PHONY: help setup env up up-no-build up-no-static down down-volumes logs status collectstatic migrate makemigrations restart restart-fe restart-fe-pilot restart-be deploy-be sync-db sync-db-full sync-db-diagnose sync-db-full-diagnose sync-media sync-media-push mirror-resync-after-event cleanup-legacy backup-db pilot-tick pilot-tick-loop pilot-tick-stop pilot-tick-restart

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
	@echo "  opzionale up/up-no-build/up-no-static:"
	@echo "    RECREATE_FRONTEND=1 # forza recreate del servizio frontend (utile dopo reboot)"
	@echo "    ALLOW_DB_REINIT=1   # override guardrail: consenti ri-init DB se volume manca"
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
	@echo "  make restart-fe ENV=prod     # su prod/mirror: niente npm locale; solo dir dati + restart frontend (statici da CI/rsync)"
	@echo "  make restart-fe-pilot ENV=dev-home # build console pilota e reload nginx (no npm in prod)"
	@echo "  make pilot-tick ENV=dev-home  # avanza motore pilotaggio (one-shot)"
	@echo "  make pilot-tick-restart ENV=dev-home # restart servizio docker pilot_tick"
	@echo "  make pilot-tick-loop ENV=dev-home # worker tick manuale foreground (debug)"
	@echo "  make pilot-tick-stop ENV=dev-home # disabilita tick runtime (flag)"
	@echo "  make restart-be ENV=dev-home # riavvia backend + daphne (carica .py aggiornati)"
	@echo "  make deploy-be ENV=prod      # rebuild backend/daphne + restart + migrate + collectstatic"
	@echo "  make restart ENV=dev-home    # restart-fe + restart-be"
	@echo "  make restart ENV=dev-home RUN_MIGRATIONS=1 RUN_PIP_INSTALL=1 RUN_COLLECTSTATIC=1"
	@echo ""
	@echo "Sync:"
	@echo "  make sync-db [SYNC_SINCE=ISO_DATETIME] # pull-only DB (backend container)"
	@echo "  make sync-db-full            # pull-only completo da 1970-01-01T00:00:00Z"
	@echo "  make sync-db-diagnose        # pull-only con diagnostica conflitti SegnoZodiacale"
	@echo "  make sync-db-full-diagnose   # full pull + diagnostica conflitti SegnoZodiacale"
	@echo "  make sync-media              # pull-only media via rsync (vedi scripts/sync_media_pull_wsl_pi_like.sh e .env.sync-media)"
	@echo "  make sync-media-push         # push-only media verso master (senza delete)"
	@echo "  make mirror-resync-after-event # full DB diagnose + media push + media pull"
	@echo ""
	@echo "Backup:"
	@echo "  make backup-db ENV=prod      # dump DB su file + rotazione (vedi scripts/backup_db_daily.sh)"

setup:
	./scripts/setup_wsl_pi_like.sh

env:
	./scripts/use_env_backend.sh --env "$(ENV)"

up:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" $(if $(filter 1,$(RECREATE_FRONTEND)),--recreate-frontend,) $(if $(filter 1,$(ALLOW_DB_REINIT)),--allow-db-reinit,)

up-no-build:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build $(if $(filter 1,$(RECREATE_FRONTEND)),--recreate-frontend,) $(if $(filter 1,$(ALLOW_DB_REINIT)),--allow-db-reinit,)

up-no-static:
	@if [ "$(CLEANUP_LEGACY)" = "1" ]; then ./scripts/cleanup_legacy_wsl_stack.sh; fi
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --skip-collectstatic $(if $(filter 1,$(RECREATE_FRONTEND)),--recreate-frontend,) $(if $(filter 1,$(ALLOW_DB_REINIT)),--allow-db-reinit,)

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
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py collectstatic --noinput

migrate:
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build --skip-collectstatic
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py migrate --noinput

makemigrations:
	./scripts/up_wsl_pi_like.sh --env "$(ENV)" --no-build --skip-collectstatic
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py makemigrations $(MAKEMIGRATIONS_APP)

# Build console pilota (frontend-pilot) → react_build_pilot, ricarica solo nginx.
# In prod/mirror: skip npm (statici da CI), copia placeholder se serve.
restart-fe-pilot:
	@if [ -d "$(CURDIR)/frontend-pilot" ]; then \
		if [ "$(ENV)" = "prod" ] || [ "$(ENV)" = "mirror" ]; then \
			echo "ENV=$(ENV): skip npm pilota (build via CI)."; \
		else \
			cd $(CURDIR)/frontend-pilot && (npm ci || npm install) && npm run build; \
			rm -rf $(CURDIR)/config/docker/nginx-docker/react_build_pilot/*; \
			cp -R $(CURDIR)/frontend-pilot/dist/. $(CURDIR)/config/docker/nginx-docker/react_build_pilot/; \
		fi; \
	else \
		echo "frontend-pilot/ non presente, skip."; \
	fi
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T frontend nginx -s reload 2>/dev/null || true

# Tick motore pilotaggio (one-shot, utile in dev / cron). Per loop continuo lanciare manualmente con --loop.
pilot-tick:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py pilot_tick

# Restart servizio docker dedicato al tick (avvio automatico con make up).
pilot-tick-restart:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml restart pilot_tick

# Worker continuo del tick (resta in foreground: usare tmux/screen o service dedicato).
pilot-tick-loop:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec backend python manage.py pilot_tick --loop --interval 5

# Stop logico: spegne il flag runtime (il worker resta in attesa).
pilot-tick-stop:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py shell -c "from pilotaggio.models import PilotRuntimeConfig; c=PilotRuntimeConfig.get_solo(); c.tick_enabled=False; c.save(update_fields=['tick_enabled','updated_at']); print('tick_enabled=False')"

# Build React → react_build, poi riavvio del servizio nginx (frontend).
# ENV=prod|mirror: non esegue npm sul server (statici da GitHub Actions + rsync); evita EACCES su node_modules e allinea al runbook Docker-first.
restart-fe:
	@if [ "$(ENV)" = "prod" ] || [ "$(ENV)" = "mirror" ]; then \
		./scripts/setup_wsl_pi_like.sh --skip-frontend-build; \
	else \
		./scripts/setup_wsl_pi_like.sh; \
	fi
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml restart frontend

# Riavvia backend + daphne così Gunicorn/Daphne carica le modifiche ai file Python (bind-mount backend).
restart-be:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml restart backend daphne
	@if [ "$(RUN_PIP_INSTALL)" = "1" ]; then \
		cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend sh -lc "python -m pip install -r requirements.txt"; \
	fi
	@if [ "$(RUN_MIGRATIONS)" = "1" ]; then \
		cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py migrate --noinput; \
	fi
	@if [ "$(RUN_COLLECTSTATIC)" = "1" ]; then \
		cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py collectstatic --noinput; \
	fi

# Deploy backend/daphne con rebuild immagini (necessario quando cambiano dipendenze di sistema in Dockerfile).
deploy-be:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml up -d --build backend daphne
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py migrate --noinput
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$(CURDIR)/backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py collectstatic --noinput

restart: restart-fe restart-be

sync-db:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py sync_edge_node --pull-only $(if $(SYNC_SINCE),--since "$(SYNC_SINCE)",)

sync-db-full:
	$(MAKE) sync-db ENV="$(ENV)" SYNC_SINCE="1970-01-01T00:00:00Z"

sync-db-diagnose:
	cd config/docker && $(COMPOSE_PROJECT_NAME_ARG) KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py sync_edge_node --pull-only --diagnose-zodiac $(if $(SYNC_SINCE),--since "$(SYNC_SINCE)",)

sync-db-full-diagnose:
	$(MAKE) sync-db-diagnose ENV="$(ENV)" SYNC_SINCE="1970-01-01T00:00:00Z"

sync-media:
	./scripts/sync_media_pull_wsl_pi_like.sh

sync-media-push:
	./scripts/sync_media_push_wsl_pi_like.sh

mirror-resync-after-event:
	./scripts/mirror_resync_after_event.sh --env "$(ENV)"

cleanup-legacy:
	./scripts/cleanup_legacy_wsl_stack.sh

backup-db:
	./scripts/backup_db_daily.sh --env "$(ENV)"
