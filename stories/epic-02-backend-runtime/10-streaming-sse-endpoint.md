# [DEVHUB-010] Streaming SSE endpoint for agent runs

**Labels:** `epic:backend-runtime` `area:api` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-008

## Story
**As a** frontend developer,
**I want** to subscribe to a run's events as SSE,
**so that** I can render tokens, tool calls, and errors progressively.

## Acceptance criteria
- [ ] `POST /threads/{thread_id}/runs` starts a run and returns `{ run_id }`.
- [ ] `GET /runs/{run_id}/events` streams SSE with the event types listed in `ARCHITECTURE.md` §7.
- [ ] Events are produced from LangGraph's `astream_events` and mapped to the typed protocol.
- [ ] Backpressure: a slow client does not block the graph (use a bounded queue per stream).
- [ ] Disconnects are detected; the run continues server-side and can be re-attached via `GET /runs/{run_id}/events?from=<seq>`.
- [ ] `event: error` carries `{ code, message, retryable }` from the typed error system.
- [ ] Heartbeat `: ping` every 15s.

## Technical notes
- Use `EventSourceResponse` (sse-starlette) or hand-roll over `StreamingResponse`.
- Sequence numbers per event so the client can resume cleanly.

## Definition of done
- `curl -N` against the endpoint shows a clean event stream for a happy path and an error path.
