COMPOSE ?= docker compose

.PHONY: up down ps logs config

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

config:
	$(COMPOSE) config
