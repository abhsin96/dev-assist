# DevHub AI — Story Index

Order of work is roughly top-to-bottom; stories within an epic can often parallelize once their `Depends on` block is satisfied.

## Epic 1 — Foundation
- DEVHUB-001 — Bootstrap monorepo with Turborepo + uv
- DEVHUB-002 — Docker Compose dev environment
- DEVHUB-003 — CI pipeline with GitHub Actions
- DEVHUB-004 — Observability: LangSmith + Sentry + structured logging
- DEVHUB-005 — Auth scaffolding (frontend + API)

## Epic 2 — Backend Agent Runtime
- DEVHUB-006 — FastAPI hexagonal skeleton + DI container
- DEVHUB-007 — Generic error handling: typed errors + RFC 7807
- DEVHUB-008 — LangGraph supervisor skeleton with Postgres checkpointer
- DEVHUB-009 — MCP client registry + per-agent allowlists
- DEVHUB-010 — Streaming SSE endpoint for agent runs

## Epic 3 — Specialist Agents
- DEVHUB-011 — PR Reviewer specialist agent
- DEVHUB-012 — Issue Triager specialist agent
- DEVHUB-013 — Doc Writer specialist agent
- DEVHUB-014 — Code Search specialist agent
- DEVHUB-015 — Human-in-the-loop interrupts (backend)

## Epic 4 — Frontend Foundation
- DEVHUB-016 — Next.js 15 + shadcn/ui + design tokens
- DEVHUB-017 — Frontend error handling: boundaries, AppError, toast bus
- DEVHUB-018 — App shell: sidebar, command bar, keyboard navigation

## Epic 5 — Chat & Streaming
- DEVHUB-019 — Thread list & thread detail pages
- DEVHUB-020 — Streaming message component (AI SDK + custom SSE)
- DEVHUB-021 — Generative UI for tool calls
- DEVHUB-022 — Agent trace viewer (in-app)
- DEVHUB-023 — HITL approval UI

## Epic 6 — MCP Management
- DEVHUB-024 — MCP connections page
- DEVHUB-025 — OAuth connector flow (GitHub, Slack)

## Epic 7 — Polish & Ops
- DEVHUB-026 — E2E test suite with Playwright
- DEVHUB-027 — Staging deployment + runbook

---

**Suggested first sprint (2 weeks, frontend-led):**
DEVHUB-001, 002, 003, 006, 007, 016, 017 — gets the rails laid for both apps.

**Suggested second sprint:**
DEVHUB-004, 005, 008, 009, 010, 018, 019 — first running end-to-end.

**Suggested third sprint (vertical demo):**
DEVHUB-011, 015, 020, 021, 023 — first full PR Review demo with HITL.
