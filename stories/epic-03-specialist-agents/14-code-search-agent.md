# [DEVHUB-014] Code Search specialist agent (lexical + semantic)

**Labels:** `epic:specialists` `area:agents` `type:feature` `priority:P2`
**Estimate:** 5 pts
**Depends on:** DEVHUB-009

## Story
**As a** developer,
**I want** to ask "where do we call X?" or "how does Y work?",
**so that** I can find code without leaving the chat.

## Acceptance criteria
- [ ] Agent allowlist: `github` (code search), `filesystem`, vector store adapter.
- [ ] Hybrid retrieval: GitHub code search for exact symbols + vector search over embedded code chunks for semantic queries.
- [ ] Result objects include `repo`, `path`, `start_line`, `end_line`, `snippet`, `score`.
- [ ] An indexer job (out of scope here, follow-up story) populates the vector store; for now use a small seeded fixture.
- [ ] Returns at most N results with citations the UI can deep-link to.
- [ ] Tests verify ranking determinism with fixed embeddings.

## Definition of done
- Demo: search a known repo for a function name and a behavioral description; both yield the right file.
