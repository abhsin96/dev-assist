# [DEVHUB-025] OAuth connector flow (GitHub, Slack)

**Labels:** `epic:mcp-management` `area:auth` `type:feature` `priority:P1`
**Estimate:** 5 pts
**Depends on:** DEVHUB-024, DEVHUB-005

## Story
**As a** user,
**I want** to grant DevHub access to GitHub and Slack via OAuth,
**so that** agents can act on my behalf with my permissions and revocable consent.

## Acceptance criteria
- [ ] OAuth start endpoints (`/connect/github/start`, `/connect/slack/start`) redirect to provider consent.
- [ ] Callback endpoints validate state, exchange code for tokens, and store tokens encrypted (AES-GCM, KMS-managed key).
- [ ] Tokens are scoped to the `mcp_connections` row; refresh tokens are rotated automatically.
- [ ] A "Revoke" action invalidates the token at the provider and deletes the local copy.
- [ ] Audit log entries for connect, refresh, revoke.
- [ ] No token ever appears in logs, traces, or error payloads (verified by a test).

## Definition of done
- A user can connect GitHub from settings, run a PR review against a private repo, then revoke and observe the next run failing with a clean `AUTH_REQUIRED` error.
