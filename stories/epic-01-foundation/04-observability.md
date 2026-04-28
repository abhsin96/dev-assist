# [DEVHUB-004] Observability: LangSmith + Sentry + structured logging

**Labels:** `epic:foundation` `area:observability` `type:chore` `priority:P1`
**Estimate:** 3 pts
**Depends on:** DEVHUB-001

## Story
**As an** on-call engineer,
**I want** every agent run, tool call, and exception to be traceable across frontend and backend,
**so that** I can debug live issues in minutes, not hours.

## Acceptance criteria
- [ ] `LANGCHAIN_TRACING_V2`, `LANGCHAIN_PROJECT`, `LANGCHAIN_API_KEY` are wired in API env; LangSmith shows graph runs end-to-end.
- [ ] Sentry SDK initialized in both `apps/web` and `apps/api`; release tagging via git SHA.
- [ ] API logs are JSON via `structlog`; every log line includes `trace_id`, `run_id` (when available), `user_id`.
- [ ] A `request_id` middleware injects `X-Request-Id` and propagates it to LangSmith metadata.
- [ ] Frontend errors carry the same `trace_id` (read from response headers or generated client-side and sent on each request).
- [ ] `docs/runbooks/observability.md` documents how to find a request across the three systems.

## Technical notes
- Pick one OTel exporter behind an env flag; do not block CI on a real backend.
- Redact secrets in log fields by default (deny-list of headers).

## Definition of done
- Triggering a known error from the UI lands the user-visible toast, a Sentry event, a structlog line, and a LangSmith trace — all sharing the same `trace_id`.
