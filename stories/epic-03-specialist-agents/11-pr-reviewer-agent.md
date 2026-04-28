# [DEVHUB-011] PR Reviewer specialist agent

**Labels:** `epic:specialists` `area:agents` `type:feature` `priority:P1`
**Estimate:** 5 pts
**Depends on:** DEVHUB-009, DEVHUB-010

## Story
**As a** developer,
**I want** to ask DevHub to review a PR by URL,
**so that** I get structured feedback (correctness, style, risk) and an optional draft GitHub comment.

## Acceptance criteria
- [ ] `domain/agents/pr_reviewer.py` defines a sub-graph or ReAct agent allowed to use the GitHub MCP server only.
- [ ] Given a PR URL, the agent fetches the diff, file list, and base context, and produces a structured review object: `{ summary, blocking[], non_blocking[], nits[], suggested_comment }`.
- [ ] The agent tags any change to security-sensitive paths (configurable list) as `blocking`.
- [ ] Posting the comment is gated by HITL approval (DEVHUB-015) — never auto-posts.
- [ ] Reflection step: a critique prompt re-checks each `blocking` item before final output.
- [ ] Unit tests with a recorded fake MCP transport cover: clean PR, PR with security-sensitive change, oversized diff (truncation behavior).
- [ ] Tracing: each tool call appears as a child run in LangSmith under the parent run.

## Definition of done
- Demoed end-to-end against a real test repo PR.
