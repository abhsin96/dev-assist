# [DEVHUB-008] LangGraph supervisor skeleton with Postgres checkpointer

**Labels:** `epic:backend-runtime` `area:agents` `type:feature` `priority:P0`
**Estimate:** 5 pts
**Depends on:** DEVHUB-006, DEVHUB-007

## Story
**As an** agent developer,
**I want** a working supervisor graph that can route to a single placeholder specialist and resume from a checkpoint,
**so that** every later agent story slots into a proven runtime.

## Acceptance criteria
- [ ] `domain/graphs/supervisor.py` builds a `StateGraph` with nodes: `supervisor`, `echo_specialist` (placeholder), `__end__`.
- [ ] `AgentState` matches `ARCHITECTURE.md` §3.
- [ ] `PostgresSaver` is wired as the checkpointer; checkpoints land in the `checkpoints` table.
- [ ] A use-case `StartRun(thread_id, user_message)` creates a run, streams events, and persists the final assistant message.
- [ ] A use-case `ResumeRun(run_id)` continues from the latest checkpoint.
- [ ] All graph errors are caught and accumulated in `state.errors`; the graph never raises out.
- [ ] Integration test: a run that triggers a tool failure surfaces an `error` event but the run still completes with a graceful assistant message.

## Technical notes
- Keep the LLM client behind a `LLMPort` interface — tests use a deterministic fake.
- Supervisor prompt lives in `domain/prompts/supervisor.md` (versioned, not hardcoded).

## Definition of done
- A `pytest` integration test runs the graph end-to-end against a real Postgres in CI.
