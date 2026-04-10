SHELL := /bin/bash

# Profili supportati: dev-home, dev-office, mirror, prod
ENV ?= dev-home
CLEANUP_LEGACY ?= 0

.PHONY: help setup env up up-no-build up-no-static down down-volumes logs status collectstatic sync-db sync-media cleanup-legacy

help:
	@echo "KOR35 monorepo helper"
	@echo ""
	@echo "Uso:"
	@echo "  make <target> [ENV=dev-home|dev-office|mirror|prod]"
	@echo "  opzionale: CLEANUP_LEGACY=1 (rimuove container legacy kor35_wsl_*)"
	@echo ""
	@echo "Target principali:"
	@echo "  make env ENV=dev-home        # crea/attiva backend/.env.<env>"
	@echo "  make setup                   # prepara runtime + build frontend"
	@echo "  make up                      # avvia stack (con build + collectstatic)"
	@echo "  make up-no-build             # avvio senza rebuild immagini"
	@echo "  make up-no-static            # avvio senza collectstatic"
	@echo "  make status                  # stato container"
	@echo "  make logs                    # log live (tutti i servizi)"
	@echo "  make down                    # stop stack"
	@echo "  make down-volumes            # stop + rimozione volumi"
	@echo "  make cleanup-legacy          # rimuove vecchi container kor35_wsl_*"
	@echo ""
	@echo "Sync:"
	@echo "  make sync-db                 # pull-only DB (backend container)"
	@echo "  make sync-media              # pull-only media via rsync"

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

sync-db:
	cd config/docker && KOR35_BACKEND_ENV_FILE="$$(pwd)/../../backend/.env.$(ENV)" docker compose -f compose.base.yml -f compose.$(ENV).yml exec -T backend python manage.py sync_edge_node --pull-only

sync-media:
	./scripts/sync_media_pull_wsl_pi_like.sh

cleanup-legacy:
	./scripts/cleanup_legacy_wsl_stack.sh
