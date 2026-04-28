# [DEVHUB-026] E2E test suite with Playwright

**Labels:** `epic:polish-ops` `area:qa` `type:chore` `priority:P1`
**Estimate:** 5 pts
**Depends on:** DEVHUB-019, DEVHUB-020, DEVHUB-023

## Story
**As a** maintainer,
**I want** an E2E suite covering the critical user journeys,
**so that** regressions are caught before release.

## Acceptance criteria
- [ ] Playwright runs against a docker-compose stack in CI (recorded MCP fixtures, deterministic LLM via fake provider).
- [ ] Suites cover: sign in, create thread, ask PR review, approve HITL, observe outcome; thread rename/delete; connection add/disable.
- [ ] Traces and videos are uploaded as CI artifacts on failure.
- [ ] Flake budget: any test flaking > 1% over a week is quarantined and a follow-up issue auto-created.

## Definition of done
- All P0 user journeys covered; CI runs the suite on every PR and nightly.
