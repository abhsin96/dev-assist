# [DEVHUB-003] CI pipeline with GitHub Actions

**Labels:** `epic:foundation` `area:ci` `type:chore` `priority:P0`
**Estimate:** 2 pts
**Depends on:** DEVHUB-001

## Story
**As a** maintainer,
**I want** every PR to run lint, type-check, unit tests, and a build for both apps,
**so that** broken code never lands on `main`.

## Acceptance criteria
- [ ] `.github/workflows/ci.yml` runs on `pull_request` and `push` to `main`.
- [ ] Jobs: `web-quality` (lint + typecheck + unit), `api-quality` (ruff + mypy + pytest), `build` (matrix for both apps).
- [ ] Caches: pnpm store, Turbo, `uv` cache.
- [ ] Required status checks documented in repo settings doc.
- [ ] PR template (`.github/pull_request_template.md`) prompts for: linked story, screenshots/recording, risk, rollout plan.

## Definition of done
- A green CI run is the prerequisite to merge; failing checks block merging via branch protection.
