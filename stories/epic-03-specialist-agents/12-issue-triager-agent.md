# [DEVHUB-012] Issue Triager specialist agent

**Labels:** `epic:specialists` `area:agents` `type:feature` `priority:P1`
**Estimate:** 5 pts
**Depends on:** DEVHUB-009, DEVHUB-010

## Story
**As an** engineering manager,
**I want** to point DevHub at a repo's open issues and get them triaged,
**so that** the team starts each morning with a prioritized backlog.

## Acceptance criteria
- [ ] Agent allowlist: `github`, `linear` (optional).
- [ ] Inputs: repo, optional filters (label, age). Outputs: per-issue `{ priority, labels[], duplicate_of?, suggested_assignee?, rationale }`.
- [ ] Duplicate detection: similarity over title + first paragraph, threshold tunable.
- [ ] All mutations (label, assign, close as duplicate) are gated by HITL approval and batched into one approval card per issue.
- [ ] Idempotent: re-running on the same issue produces the same triage when the input hasn't changed (cache by issue `updated_at`).
- [ ] Unit tests with recorded MCP fixtures.

## Definition of done
- Manual demo: triage 10 issues on a sandbox repo, approve a subset, observe correct GitHub state changes.
