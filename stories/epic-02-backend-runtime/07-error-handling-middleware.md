# [DEVHUB-007] Generic error handling: typed errors + RFC 7807 middleware

**Labels:** `epic:backend-runtime` `area:reliability` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-006

## Story
**As a** frontend developer,
**I want** the API to return structured, typed errors with a stable `code`,
**so that** I can map them deterministically to UI states (toast, inline message, retry).

## Acceptance criteria
- [ ] `core/errors.py` defines `DevHubError` and the subclasses listed in `ARCHITECTURE.md` §6.
- [ ] A FastAPI `exception_handler` converts every `DevHubError` to `application/problem+json` with fields `type`, `title`, `status`, `code`, `detail`, `instance`, `traceId`, optional `retryAfter`.
- [ ] Unknown exceptions are logged at ERROR with stack trace and returned as a generic `INTERNAL_ERROR` 500 — never leaking internals.
- [ ] Validation errors from Pydantic become `VALIDATION_ERROR` 422 with a normalized `errors[]` array (path + message).
- [ ] A `with_retries(retriable_codes, max_attempts, base_delay)` helper exists for wrapping flaky calls.
- [ ] Unit tests cover: known error → correct shape; unknown error → 500 sanitized; validation error → 422 normalized.

## Technical notes
- Stable `code` strings live in a single enum/registry so the frontend can ship a typed map.
- Always include `traceId` so users can give support a single string to grep on.

## Definition of done
- Frontend (DEVHUB-017) can rely on `code` for branching and never has to parse free-form messages.
