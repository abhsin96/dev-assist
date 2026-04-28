# [DEVHUB-013] Doc Writer specialist agent

**Labels:** `epic:specialists` `area:agents` `type:feature` `priority:P2`
**Estimate:** 3 pts
**Depends on:** DEVHUB-009, DEVHUB-010

## Story
**As a** developer,
**I want** DevHub to draft or update README / module docs for a repo,
**so that** documentation keeps up with the code.

## Acceptance criteria
- [ ] Agent allowlist: `github` (read), `filesystem` (read).
- [ ] Generates a Markdown draft with sections: overview, install, quickstart, architecture overview, examples.
- [ ] When updating an existing doc, produces a diff against the current file and surfaces it as a `tool_result` for the UI to render.
- [ ] Writing back to the repo is gated by HITL approval and uses a PR (never direct push to default branch).
- [ ] Unit tests cover: greenfield README, README update diff, module-level docstring sweep.

## Definition of done
- A demo repo with no README ends up with a useful draft in under 60 seconds.
