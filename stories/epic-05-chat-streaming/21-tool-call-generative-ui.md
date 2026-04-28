# [DEVHUB-021] Generative UI for tool calls (PR diffs, issues, search results)

**Labels:** `epic:chat-streaming` `area:web` `type:feature` `priority:P1`
**Estimate:** 5 pts
**Depends on:** DEVHUB-020

## Story
**As a** user,
**I want** tool results to render as rich, interactive cards instead of raw JSON,
**so that** I can scan results quickly and click through.

## Acceptance criteria
- [ ] A `ToolRenderer` registry maps `tool_name` → React component.
- [ ] Components shipped in v1: `<PRDiffCard>`, `<IssueCard>`, `<CodeSearchResult>`, `<DocDiffCard>`.
- [ ] Each card has: loading state (while tool runs), success state, error state with retry.
- [ ] Cards collapse by default if their payload is large; clicking expands inline.
- [ ] Unknown tools fall back to a generic JSON viewer card.
- [ ] Cards are accessible (keyboard expand/collapse, proper headings, ARIA labels).

## Definition of done
- A live demo: a PR review thread renders cards for diff fetch, suggested comment, and HITL approval.
