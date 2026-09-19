# Andalusia drought monitor — Docker helpers (compose file lives under docker/)
COMPOSE := docker compose -f docker/docker-compose.yml
# Load secrets from repo-root .env on every compose invocation (deploy + local).
ifneq (,$(wildcard .env))
  COMPOSE += --env-file .env
endif

.PHONY: help up down stop ps logs build pull dashboard-up dashboard-down dashboard-logs

help:
	@echo "Targets:"
	@echo "  make up              - start full stack (detached)"
	@echo "  make down            - stop stack + remove containers/networks"
	@echo "  make stop            - stop containers (keep them)"
	@echo "  make ps              - compose ps"
	@echo "  make logs            - tail all service logs"
	@echo "  make build           - build images"
	@echo "  make dashboard-up    - start dashboard-api + dashboard-frontend"
	@echo "  make dashboard-down  - stop dashboard services"
	@echo "  make dashboard-logs  - tail dashboard-api + dashboard-frontend logs"
	@echo ""
	@echo "Secrets: copy .env.example -> .env and set VITE_CARTO_API_KEY (gitignored)."

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

stop:
	$(COMPOSE) stop

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

pull:
	$(COMPOSE) pull

dashboard-up:
	$(COMPOSE) up -d --build dashboard-api dashboard-frontend

dashboard-down:
	$(COMPOSE) stop dashboard-api dashboard-frontend

dashboard-logs:
	$(COMPOSE) logs -f dashboard-api dashboard-frontend
