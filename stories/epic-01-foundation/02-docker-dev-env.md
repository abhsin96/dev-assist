# [DEVHUB-002] Docker Compose dev environment (Postgres, Redis, MCP servers)

**Labels:** `epic:foundation` `area:infra` `type:chore` `priority:P0`
**Estimate:** 2 pts
**Depends on:** DEVHUB-001

## Story
**As a** developer,
**I want** to bring up Postgres, Redis, and at least one reference MCP server with a single command,
**so that** I can run the full stack locally without manual setup.

## Acceptance criteria
- [ ] `infra/docker/docker-compose.yml` defines services: `postgres:16`, `redis:7`, `mcp-github` (reference MCP GitHub server), with healthchecks.
- [ ] Volumes are named so DB state survives `docker compose down`.
- [ ] A `make up` / `make down` / `make logs` helper exists at the repo root.
- [ ] `apps/api` reads connection strings from `.env` (a committed `.env.example` documents every variable).
- [ ] Postgres is initialized with a `devhub` database and a non-superuser role.
- [ ] README has a "Run locally" section pointing to this setup.

## Technical notes
- Use Docker secrets/`.env` for tokens; never commit credentials.
- The MCP GitHub server runs in a container with a `GITHUB_TOKEN` env var; the API connects to it via stdio-over-socket or HTTP transport (whichever the chosen MCP server supports).

## Definition of done
- `make up` followed by `pnpm dev` produces a working stack on a fresh laptop.
