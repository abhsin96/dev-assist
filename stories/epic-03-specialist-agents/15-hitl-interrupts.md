# [DEVHUB-015] Human-in-the-loop interrupts (backend)

**Labels:** `epic:specialists` `area:agents` `type:feature` `priority:P0`
**Estimate:** 5 pts
**Depends on:** DEVHUB-008, DEVHUB-009

## Story
**As a** user,
**I want** DevHub to pause and ask for approval before destructive actions (post comment, close issue, push doc),
**so that** I stay in control.

## Acceptance criteria
- [ ] LangGraph `interrupt()` is invoked whenever a tool with `requires_approval=True` is about to run.
- [ ] An `HITLRequest` (with `tool_call`, `summary`, `risk`, `expires_at`) is persisted and emitted to the run stream as `event: interrupt`.
- [ ] `POST /runs/{run_id}/approvals` accepts `{ approval_id, decision: "approve"|"reject", patched_args? }` and resumes the run.
- [ ] On reject, the agent is told the user denied the action and continues (it should propose an alternative or stop).
- [ ] Approvals are recorded in `audit_log` with user id, timestamp, decision, and patched args.
- [ ] Expired approvals automatically reject after `expires_at` (default 30m).

## Definition of done
- An end-to-end test pauses a PR Reviewer run, approves the comment via API, and observes the comment posted to a sandbox repo.
