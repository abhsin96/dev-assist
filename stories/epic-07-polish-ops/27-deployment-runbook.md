# [DEVHUB-027] Staging deployment + runbook

**Labels:** `epic:polish-ops` `area:infra` `type:chore` `priority:P2`
**Estimate:** 5 pts
**Depends on:** DEVHUB-003, DEVHUB-004

## Story
**As a** team,
**we want** a single-command deploy to a staging environment with a documented runbook,
**so that** internal users can dogfood DevHub.

## Acceptance criteria
- [ ] Web → Vercel project linked to `main`.
- [ ] API → Fly.io (or Render) app with autoscaling between 1 and 3 machines.
- [ ] Postgres → Neon staging branch; Redis → Upstash.
- [ ] Secrets management documented; no plaintext secrets in repo or CI logs.
- [ ] `docs/runbooks/deploy.md`: deploy, rollback, restart MCP sidecars, rotate keys.
- [ ] Synthetic check (uptime ping + a `/healthz` + a scripted run) runs every 5 min and pages on failure.

## Definition of done
- A new dev can deploy a fresh staging stack from scratch by following the runbook in under 60 minutes.
