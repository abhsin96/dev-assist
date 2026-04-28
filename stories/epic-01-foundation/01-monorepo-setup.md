# [DEVHUB-001] Bootstrap monorepo with Turborepo + uv

**Labels:** `epic:foundation` `area:repo` `type:chore` `priority:P0`
**Estimate:** 3 pts
**Depends on:** —

## Story
**As a** developer on DevHub AI,
**I want** a single repository that hosts the Next.js web app and the FastAPI service with shared tooling,
**so that** I can run, lint, type-check, and test both sides with one command and share types end-to-end.

## Context
The system has two runtimes (Node and Python). We want a JS/TS monorepo via `pnpm` + `turborepo` for the web app and shared packages, with the Python service living alongside under `apps/api/` managed by `uv`. A shared OpenAPI → TS types pipeline keeps the contract honest.

## Acceptance criteria
- [ ] Repo root has `pnpm-workspace.yaml`, `turbo.json`, `package.json` with `dev`, `build`, `lint`, `typecheck`, `test` scripts wired through Turbo.
- [ ] `apps/web/` is a Next.js 15 app (TypeScript, App Router, ESLint, Tailwind v4).
- [ ] `apps/api/` is a Python 3.12 project managed by `uv` with `ruff`, `mypy`, `pytest` configured.
- [ ] `packages/shared-types/` exists; running `pnpm gen:types` regenerates TS types from `apps/api`'s OpenAPI export.
- [ ] `pnpm dev` starts web on `:3000`, API on `:8000` concurrently (via Turbo).
- [ ] Pre-commit hook (`lefthook` or `husky`) runs `lint-staged` and the Python equivalent on `apps/api/`.
- [ ] Root `README.md` documents `pnpm install`, `uv sync`, and the dev command.

## Technical notes
- Use `corepack` to pin pnpm version.
- Turborepo remote cache off for now (can add later).
- For OpenAPI → TS, use `openapi-typescript` driven by FastAPI's `/openapi.json` (served only in dev).

## Definition of done
- A new contributor can clone the repo, run two install commands and one dev command, and see both apps responding.
- CI (next story) runs all tasks via `turbo run` matrix.
