# Free Deployment Guide

**Last verified:** April 2026  
**Goal:** Run the full DevHub stack at $0/month using free tiers.

> Free tiers change. Verify limits at each provider's pricing page before deploying.

---

## Stack

| Layer | Service | Free limits |
|-------|---------|-------------|
| Frontend (Next.js) | [Vercel Hobby](https://vercel.com/pricing) | 100 GB bandwidth, 100 GB-hrs serverless |
| API (FastAPI) | [Render Free Web Service](https://render.com/pricing) | 750 hrs/month, spins down after 15 min idle |
| PostgreSQL | [Neon Free](https://neon.tech/pricing) | 0.5 GB storage, 1 project |
| Redis | [Upstash Free](https://upstash.com/pricing) | 256 MB, 10,000 commands/day |
| Auth (GitHub OAuth) | GitHub | Free |
| MCP GitHub server | Bundled into API process | — |

**What you won't have on free tiers:**
- LangSmith tracing (requires paid plan or self-host)
- Sentry error tracking (free tier covers 5,000 errors/month — usable)
- Always-on API (Render free spins down; first request takes ~30 s to wake)

---

## Prerequisites

Install once:

```bash
# Vercel CLI
npm install -g vercel

# Render — no CLI needed; use the dashboard
```

Accounts to create (all free):

- [vercel.com](https://vercel.com) — sign in with GitHub
- [render.com](https://render.com) — sign in with GitHub
- [neon.tech](https://neon.tech) — sign in with GitHub
- [upstash.com](https://upstash.com) — sign in with GitHub
- GitHub OAuth App (instructions below)

---

## Step 1 — Neon (PostgreSQL)

1. Create a new project: **devhub**
2. Note the connection string from the dashboard — it looks like:

   ```
   postgresql://user:password@ep-xxx.us-east-1.aws.neon.tech/devhub?sslmode=require
   ```

3. Run the schema migrations after the API is deployed (Step 3).

---

## Step 2 — Upstash (Redis)

1. Create a new database: **devhub-redis**, region closest to your Render region.
2. Copy the **Redis URL** (starts with `rediss://`).

---

## Step 3 — Render (FastAPI)

### Create the web service

1. New → **Web Service** → connect your GitHub repo.
2. Settings:

   | Field | Value |
   |-------|-------|
   | Name | `devhub-api` |
   | Root Directory | `apps/api` |
   | Runtime | **Python 3** |
   | Build Command | `pip install uv && uv sync --frozen` |
   | Start Command | `uv run uvicorn devhub.main:app --host 0.0.0.0 --port $PORT` |
   | Plan | **Free** |
   | Region | Oregon (or closest to Neon region) |
   | Health Check Path | `/health` |

### Set environment variables

In the Render dashboard → Environment, add:

```
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_URL=<Neon connection string from Step 1>
REDIS_URL=<Upstash Redis URL from Step 2>
API_JWT_SECRET=<generate: openssl rand -hex 32>
SECRET_KEY=<generate: openssl rand -hex 32>
OAUTH_ENCRYPTION_KEY=<generate: openssl rand -hex 32>
ANTHROPIC_API_KEY=<your key>
GITHUB_CLIENT_ID=<from Step 5>
GITHUB_CLIENT_SECRET=<from Step 5>
FRONTEND_URL=https://<your-vercel-domain>.vercel.app
CORS_ORIGINS=https://<your-vercel-domain>.vercel.app
```

Leave `LANGCHAIN_TRACING_V2`, `SENTRY_DSN`, `LANGCHAIN_API_KEY` empty to disable those integrations.

### Run database migrations

After the first deploy succeeds, open the Render shell (or use the Render dashboard "Shell" tab):

```bash
uv run alembic upgrade head
```

### Keep the API warm (optional)

Render free services sleep after 15 minutes of inactivity. To avoid the cold-start delay, set up a free cron ping using [cron-job.org](https://cron-job.org):

- URL: `https://devhub-api.onrender.com/health`
- Interval: every 10 minutes

---

## Step 4 — Vercel (Next.js)

### Deploy

```bash
cd apps/web
vercel
```

Follow the prompts: link to your GitHub repo, set the framework to **Next.js**.

Or connect via the Vercel dashboard → Import Git Repository → select `devhub`, set **Root Directory** to `apps/web`.

### Set environment variables

In Vercel → Project Settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=https://devhub-api.onrender.com
NEXTAUTH_URL=https://<your-vercel-domain>.vercel.app
NEXTAUTH_SECRET=<generate: openssl rand -hex 32>
GITHUB_CLIENT_ID=<from Step 5>
GITHUB_CLIENT_SECRET=<from Step 5>
```

For Sentry (optional, free tier):

```
NEXT_PUBLIC_SENTRY_DSN=<your Sentry DSN>
SENTRY_AUTH_TOKEN=<your Sentry auth token>
SENTRY_ORG=<your org slug>
SENTRY_PROJECT=devhub-web
```

Trigger a redeploy after saving env vars.

---

## Step 5 — GitHub OAuth App

1. GitHub → Settings → Developer settings → OAuth Apps → **New OAuth App**.
2. Fill in:

   | Field | Value |
   |-------|-------|
   | Application name | DevHub AI |
   | Homepage URL | `https://<your-vercel-domain>.vercel.app` |
   | Callback URL | `https://<your-vercel-domain>.vercel.app/api/auth/callback/github` |

3. Copy **Client ID** and **Client Secret** into Render and Vercel env vars (Step 3 and Step 4).

---

## Step 6 — Smoke test

```bash
# API health
curl https://devhub-api.onrender.com/health

# Readiness (checks Postgres + Redis)
curl https://devhub-api.onrender.com/readyz
```

Then open your Vercel URL, sign in with GitHub, and create a thread.

---

## Known free-tier constraints

| Constraint | Impact | Workaround |
|------------|--------|------------|
| Render spins down after 15 min idle | First request ~30 s | cron-job.org ping (Step 3) |
| Neon 0.5 GB storage | Checkpointer state grows | Run `SELECT pg_size_pretty(pg_database_size('devhub'));` periodically; truncate old runs |
| Upstash 10,000 commands/day | Each streaming run uses ~20–50 commands | Enough for ~200–500 runs/day; upgrade if needed |
| Vercel 100 GB bandwidth | Fine for personal/demo use | Monitor in Vercel dashboard |

---

## Teardown

To avoid any surprise charges if you upgrade a service accidentally:

```bash
# Delete Neon project from dashboard
# Delete Render service from dashboard
# Delete Upstash database from dashboard
# Delete Vercel project: vercel remove devhub-web
```
