# [DEVHUB-017] Frontend error handling: boundaries, AppError, toast bus

**Labels:** `epic:frontend-foundation` `area:web` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-007, DEVHUB-016

## Story
**As a** user,
**I want** errors to never break the whole app and to show a clear, actionable message,
**so that** I can recover or retry without reloading.

## Acceptance criteria
- [ ] `app/error.tsx` and a route-level `error.tsx` per top-level segment (`(chat)`, `settings`).
- [ ] A shared `<AsyncBoundary>` (Suspense + ErrorBoundary) wraps every async client island.
- [ ] `lib/errors/AppError.ts` is the typed mirror of backend `DevHubError`; `parseProblem(response)` produces an `AppError`.
- [ ] The API client (`lib/api/client.ts`) throws `AppError` for any non-2xx; never returns raw error JSON to callers.
- [ ] A central `toast` bus (Sonner) renders `AppError`s with: title from `code`, body from `detail`, and a "Copy traceId" action.
- [ ] Retry-able errors show a "Retry" action that re-invokes the original mutation/query.
- [ ] Unit tests cover the `code → UI` mapping for at least 6 representative codes.

## Technical notes
- Map `code` → user-facing copy in a single `i18n` table; never rely on backend free-form `detail` for primary copy.

## Definition of done
- Throwing a known error in any feature shows the right toast; throwing in a route segment renders the segment's `error.tsx` with a "Try again" button.
