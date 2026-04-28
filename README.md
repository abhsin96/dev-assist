# DevHub AI — Developer Productivity Hub

> A multi-agent assistant for engineering teams. Triage GitHub issues, review PRs, generate docs, search code, and summarize team activity — through a single conversational UI backed by a LangGraph supervisor and MCP-connected tools.

## TL;DR

- **Backend:** Python 3.12 + FastAPI + LangGraph (supervisor + specialist agents) + LangSmith tracing.
- **Frontend:** Next.js (App Router) + TypeScript + shadcn/ui + Vercel AI SDK for streaming.
- **Integrations:** MCP servers for GitHub, Slack, Linear, Filesystem, Web — connected through a unified MCP client layer.
- **Persistence:** Postgres (threads, runs, checkpoints) + Redis (pub/sub, cache).
- **Observability:** LangSmith (agent traces) + Sentry (errors) + OpenTelemetry (spans/metrics).

## Repository layout

```
devhub-ai/
├── apps/
│   ├── web/                 # Next.js frontend
│   └── api/                 # FastAPI + LangGraph backend
├── packages/
│   ├── shared-types/        # Generated TS types from Pydantic schemas
│   └── ui/                  # Shared shadcn/ui components (re-exports)
├── infra/
│   ├── docker/              # Dockerfiles + compose
│   └── terraform/           # Cloud infra (later)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ADRs/                # Architecture Decision Records
│   └── runbooks/
└── stories/                 # GitHub-ready story drafts
```

## Getting started

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 20 (managed via nvm)
- [pnpm](https://pnpm.io/) ≥ 10 (managed via corepack)
- [uv](https://docs.astral.sh/uv/) ≥ 0.4 (`brew install uv`)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) ≥ 4.x (for Postgres, Redis, MCP servers)

### Run locally

**1. Configure environment**

```bash
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD and GITHUB_TOKEN
```

**2. Start infrastructure**

```bash
make up
```

This brings up Postgres 16, Redis 7, and the GitHub MCP server. Postgres is initialized with a `devhub` database and a `devhub_app` role automatically.

**3. Install app dependencies**

```bash
# JavaScript / TypeScript (all workspaces)
pnpm install

# Python (apps/api)
cd apps/api && uv sync
```

**4. Start development servers**

```bash
pnpm dev
```

| App | URL |
|-----|-----|
| Next.js frontend | http://localhost:3000 |
| FastAPI backend  | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| GitHub MCP server | http://localhost:3001 |

### Infrastructure commands

```bash
make up      # start Postgres, Redis, MCP servers (detached, waits for healthy)
make down    # stop containers (volumes preserved)
make logs    # tail all service logs
make ps      # show running containers
make seed    # load demo data (API must be running)
```

### Other app commands

```bash
pnpm build       # production build (all apps)
pnpm lint        # lint all workspaces
pnpm typecheck   # type-check all workspaces
pnpm test        # run all test suites
pnpm gen:types   # regenerate TS types from FastAPI OpenAPI schema (API must be running)
```

### Pre-commit hooks

Lefthook runs `lint-staged` on JS/TS files and `ruff` + `mypy` on Python files before each commit. Hooks are installed automatically on `pnpm install` (via lefthook's postinstall).

## How to use this folder

- `ARCHITECTURE.md` — system design, agent topology, design patterns.
- `stories/` — one `.md` file per GitHub Issue, grouped by epic. Copy the body of each into a new GitHub Issue; titles and labels are at the top.
- Stories are ordered by epic and dependency. The "Depends on" block tells you which stories must close first.

## Project goals

1. Show off LangGraph multi-agent orchestration with real, useful workflows.
2. Demonstrate MCP as the universal tool/data plane.
3. Ship a polished, production-grade Next.js UI that feels like Linear meets ChatGPT.
4. Keep the architecture clean enough that adding a new agent or MCP server is a one-day task.
