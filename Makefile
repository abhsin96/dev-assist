COMPOSE := docker compose -f infra/docker/docker-compose.yml --env-file .env

.PHONY: up down logs ps seed

## Bring up all infrastructure services (Postgres, Redis, MCP servers)
up:
	$(COMPOSE) up -d --wait

## Stop and remove containers (volumes are preserved)
down:
	$(COMPOSE) down

## Tail logs from all services (Ctrl-C to quit)
logs:
	$(COMPOSE) logs -f

## Show running service status
ps:
	$(COMPOSE) ps

## Populate the database with demo data (requires API to be running)
seed:
	cd apps/api && uv run python -m devhub.scripts.seed
