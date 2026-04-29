# Deployment Runbook

**Target:** Staging environment  
**Audience:** Any developer with repo access  
**Goal:** A new dev can deploy a fresh staging stack from scratch in under 60 minutes.

---

## Architecture overview

| Layer    | Service                   | Notes                                  |
|----------|---------------------------|----------------------------------------|
| Web      | Vercel (auto-deploy)      | Linked to `main`; no manual steps      |
| API      | Fly.io `devhub-api-staging` | 1–3 shared VMs, rolling deploys      |
| Postgres | Neon — staging branch     | Branched from `main` at setup time     |
| Redis    | Upstash — staging DB      | Single-region; TLS required            |
| MCP      | Fly.io sidecar machine    | `devhub-mcp-github-staging`            |
| Secrets  | Fly.io secrets + Vercel env | Never in repo or CI logs             |

---

## Prerequisites

Install these tools once:

```bash
brew install flyctl
npm install -g vercel
```

Authenticate:

```bash
flyctl auth login
vercel login
```

---

## First-time setup (new stack from scratch)

### 1. Provision Neon Postgres

1. Go to [console.neon.tech](https://console.neon.tech) → create project `devhub-staging`.
2. Create a branch `staging` from `main`.
3. Copy the **connection string** (pooled, asyncpg-compatible):
   ```
   postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Run migrations against the branch:
   ```bash
   DATABASE_URL="<neon-connection-string>" uv run --project apps/api \
     alembic -c apps/api/alembic.ini upgrade head
   ```

### 2. Provision Upstash Redis

1. Go to [console.upstash.com](https://console.upstash.com) → create database `devhub-staging`, region `us-east-1`.
2. Enable **TLS**. Copy the `rediss://` URL.

### 3. Create the Fly.io API app

```bash
cd apps/api

# Create app (one-time)
flyctl apps create devhub-api-staging

# Configure autoscaling (1–3 machines)
flyctl autoscale set min=1 max=3 --app devhub-api-staging

# Set secrets (never put these in fly.toml or any committed file)
flyctl secrets set \
  DATABASE_URL="<neon-connection-string>" \
  REDIS_URL="<upstash-rediss-url>" \
  API_JWT_SECRET="$(openssl rand -hex 32)" \
  SECRET_KEY="$(openssl rand -hex 32)" \
  OAUTH_ENCRYPTION_KEY="$(openssl rand -hex 32)" \
  ANTHROPIC_API_KEY="<key>" \
  GITHUB_CLIENT_ID="<id>" \
  GITHUB_CLIENT_SECRET="<secret>" \
  SLACK_CLIENT_ID="<id>" \
  SLACK_CLIENT_SECRET="<secret>" \
  SENTRY_DSN="<dsn>" \
  LANGCHAIN_API_KEY="<key>" \
  FRONTEND_URL="https://devhub-staging.vercel.app" \
  --app devhub-api-staging

# First deploy
flyctl deploy --remote-only --app devhub-api-staging
```

### 4. Deploy the MCP GitHub sidecar

```bash
# Create the sidecar app
flyctl apps create devhub-mcp-github-staging

flyctl secrets set \
  GITHUB_PERSONAL_ACCESS_TOKEN="<github-pat>" \
  --app devhub-mcp-github-staging

# Deploy using the MCP sidecar image
flyctl deploy \
  --app devhub-mcp-github-staging \
  --image ghcr.io/github/github-mcp-server:latest \
  --port 3001

# Update API to point to the sidecar's private address
flyctl secrets set \
  MCP_GITHUB_URL="http://devhub-mcp-github-staging.internal:3001" \
  --app devhub-api-staging
```

### 5. Link the Vercel project

```bash
cd apps/web
vercel link   # select "devhub" org → "devhub-web-staging" project
```

Set environment variables in the Vercel dashboard (or CLI):

```bash
vercel env add NEXT_PUBLIC_API_URL production <<< "https://devhub-api-staging.fly.dev"
vercel env add NEXTAUTH_SECRET production <<< "$(openssl rand -hex 32)"
vercel env add NEXTAUTH_URL production <<< "https://devhub-staging.vercel.app"
vercel env add API_JWT_SECRET production <<< "<same value set in Fly secrets>"
vercel env add GITHUB_ID production <<< "<github-oauth-app-client-id>"
vercel env add GITHUB_SECRET production <<< "<github-oauth-app-client-secret>"
vercel env add SENTRY_ORG production <<< "<org-slug>"
vercel env add SENTRY_PROJECT production <<< "<project-slug>"
vercel env add SENTRY_AUTH_TOKEN production <<< "<token>"
```

> **Important:** `API_JWT_SECRET` must match the value set as a Fly secret. Both sides sign/verify the same HS256 JWTs.

Trigger first web deploy:

```bash
vercel --prod
```

### 6. Add GitHub Actions secrets

In the repo → Settings → Secrets → Actions, add:

| Secret | Value |
|--------|-------|
| `FLY_API_TOKEN` | `flyctl auth token` |
| `VERCEL_TOKEN` | Vercel personal token |
| `VERCEL_ORG_ID` | From `vercel whoami --json` |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json` after `vercel link` |
| `SYNTHETIC_API_TOKEN` | A long-lived JWT minted with `API_JWT_SECRET` for the synthetic test user |

### 7. Verify

```bash
# API health
curl https://devhub-api-staging.fly.dev/healthz
curl https://devhub-api-staging.fly.dev/readyz

# Web
curl -I https://devhub-staging.vercel.app
```

Both should return 200. If `/readyz` shows a degraded service, check the relevant section below.

---

## Routine deploy (push to main)

Every push to `main` that passes CI automatically:
- Deploys the API to Fly.io via `.github/workflows/deploy.yml`
- Deploys the web app to Vercel via git integration

No manual action required. To deploy manually:

```bash
# API
flyctl deploy --remote-only --app devhub-api-staging  # from apps/api/

# Web
vercel --prod  # from apps/web/
```

---

## Rollback

### API rollback

```bash
# List recent releases
flyctl releases --app devhub-api-staging

# Roll back to a specific version
flyctl deploy --image <image-ref-from-releases> --app devhub-api-staging

# Or roll back one version
flyctl releases rollback --app devhub-api-staging
```

### Web rollback

In the Vercel dashboard → Deployments → find the last good deployment → **Promote to Production**.

Or via CLI:

```bash
vercel rollback <deployment-url>
```

---

## Restart MCP sidecars

The MCP GitHub sidecar runs as a separate Fly.io app. Restart it without affecting the API:

```bash
# Restart all machines in the sidecar app
flyctl apps restart devhub-mcp-github-staging

# Check sidecar health
flyctl status --app devhub-mcp-github-staging

# Tail logs
flyctl logs --app devhub-mcp-github-staging
```

If the sidecar is crashlooping, SSH in to inspect:

```bash
flyctl ssh console --app devhub-mcp-github-staging
```

After fixing the sidecar, verify the API's `/readyz` endpoint shows `"mcp": "ok"`:

```bash
curl https://devhub-api-staging.fly.dev/readyz | jq .
```

---

## Rotate secrets / keys

### Rotate `API_JWT_SECRET` (breaks all active sessions)

```bash
NEW_SECRET=$(openssl rand -hex 32)

# Update API
flyctl secrets set API_JWT_SECRET="$NEW_SECRET" --app devhub-api-staging

# Update web (Vercel env)
vercel env rm API_JWT_SECRET production
vercel env add API_JWT_SECRET production <<< "$NEW_SECRET"

# Redeploy both so they read the new secret simultaneously
flyctl deploy --remote-only --app devhub-api-staging
vercel --prod

# Update the synthetic check secret too
gh secret set SYNTHETIC_API_TOKEN --body "<mint a new long-lived JWT with the new secret>"
```

### Rotate `OAUTH_ENCRYPTION_KEY` (invalidates stored OAuth tokens)

```bash
# 1. Generate new key
NEW_KEY=$(openssl rand -hex 32)

# 2. Update Fly secret
flyctl secrets set OAUTH_ENCRYPTION_KEY="$NEW_KEY" --app devhub-api-staging

# 3. All stored OAuth connections are now undecryptable — users must reconnect.
#    Notify affected users before rotating in production.

# 4. Redeploy
flyctl deploy --remote-only --app devhub-api-staging
```

### Rotate `SECRET_KEY` (invalidates server-side sessions)

```bash
flyctl secrets set SECRET_KEY="$(openssl rand -hex 32)" --app devhub-api-staging
flyctl deploy --remote-only --app devhub-api-staging
```

### Rotate GitHub / Slack OAuth credentials

1. Issue new credentials from the provider's developer console.
2. Update both Fly secrets and Vercel env vars:
   ```bash
   flyctl secrets set GITHUB_CLIENT_ID="..." GITHUB_CLIENT_SECRET="..." --app devhub-api-staging
   vercel env rm GITHUB_ID production && vercel env add GITHUB_ID production <<< "..."
   vercel env rm GITHUB_SECRET production && vercel env add GITHUB_SECRET production <<< "..."
   ```
3. Deploy API and web.
4. Revoke the old credentials at the provider.

---

## Secrets policy

- **No secret in any committed file.** `fly.toml` and `vercel.json` contain only non-sensitive env vars.
- **No secret in CI logs.** Secrets are passed via GitHub Actions secrets (masked) or Fly/Vercel secret stores.
- **Rotation cadence:** Rotate `API_JWT_SECRET` and `SECRET_KEY` every 90 days. `OAUTH_ENCRYPTION_KEY` only on suspected compromise (rotation is destructive).
- **Audit:** `flyctl secrets list --app devhub-api-staging` shows secret names (never values). Vercel dashboard shows env var names under Project → Settings → Environment Variables.

---

## Monitoring and alerting

| Signal | Source |
|--------|--------|
| Uptime + `/healthz` + scripted run | GitHub Actions `synthetic-check.yml` — every 5 min |
| Failures open a `synthetic-alert` issue | Same workflow — de-duped (one open issue at a time) |
| Error traces | Sentry — `devhub-api` project |
| Structured logs | `flyctl logs --app devhub-api-staging` |
| LLM traces | LangSmith — project `devhub-ai` |

### Check synthetic alert status

```bash
# List open synthetic-alert issues
gh issue list --label synthetic-alert
```

### Silence a false-positive alert

Close the GitHub issue manually after confirming the system is healthy:

```bash
gh issue close <issue-number> --comment "False positive — confirmed healthy at $(date -u)"
```

---

## Troubleshooting quick reference

| Symptom | First step |
|---------|-----------|
| `/readyz` shows `postgres: degraded` | Check Neon console for branch pauses; `flyctl secrets` to verify `DATABASE_URL` |
| `/readyz` shows `redis: degraded` | Check Upstash console; verify `REDIS_URL` uses `rediss://` |
| `/readyz` shows `mcp: degraded` | Restart MCP sidecar (see above) |
| 401 on all API routes | `API_JWT_SECRET` mismatch between web and API — check both secrets |
| OAuth connect broken after key rotation | Expected — users must reconnect; see rotate `OAUTH_ENCRYPTION_KEY` above |
| Fly machine count at 0 | `flyctl autoscale set min=1 --app devhub-api-staging` to restore floor |
| Vercel build failing | Check `SENTRY_AUTH_TOKEN` is set; otherwise Sentry source-map upload fails the build |
