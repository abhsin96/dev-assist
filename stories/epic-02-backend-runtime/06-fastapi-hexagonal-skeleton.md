# [DEVHUB-006] FastAPI hexagonal skeleton + DI container

**Labels:** `epic:backend-runtime` `area:api` `type:feature` `priority:P0`
**Estimate:** 5 pts
**Depends on:** DEVHUB-001, DEVHUB-002

## Story
**As a** backend developer,
**I want** the API to follow a clean hexagonal layout with explicit ports and adapters,
**so that** I can swap LLM providers, MCP transports, and persistence without touching agent code.

## Acceptance criteria
- [ ] Folder layout matches `ARCHITECTURE.md` §5 (`api/`, `application/`, `domain/`, `adapters/`, `core/`).
- [ ] A DI container (e.g. `dependency-injector` or hand-rolled with `Annotated[..., Depends(...)]` factories) wires repos, MCP registry, LLM client into use-cases.
- [ ] `domain/*` modules import only from `domain/` and `core/`.
- [ ] An import-linter config enforces the dependency rule in CI.
- [ ] `GET /healthz` returns `{ status: "ok", version, gitSha }`.
- [ ] `GET /readyz` checks Postgres + Redis + MCP registry status.
- [ ] OpenAPI is published at `/openapi.json` only when `ENV != "prod"`.

## Technical notes
- Pydantic v2 for schemas; `model_config = ConfigDict(frozen=True)` for value objects.
- SQLAlchemy 2.x async session factory; one session per request via dependency.

## Definition of done
- `pytest` covers a vertical slice (router → use-case → repo) using a fake adapter implementation, demonstrating the layering works.
