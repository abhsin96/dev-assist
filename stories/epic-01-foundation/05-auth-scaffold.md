# [DEVHUB-005] Auth scaffolding (frontend + API)

**Labels:** `epic:foundation` `area:auth` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-001, DEVHUB-002

## Story
**As a** user,
**I want** to sign in with my GitHub account,
**so that** my threads and connector tokens are scoped to me.

## Acceptance criteria
- [ ] `apps/web` uses Auth.js (NextAuth v5) with the GitHub provider; session is stored in an HTTP-only cookie.
- [ ] `apps/api` validates a short-lived JWT minted by the web BFF; rejects unsigned/expired tokens with `401` and a `problem+json` body.
- [ ] A `users` table is created on first login; subsequent logins reuse the row.
- [ ] Sign-in / sign-out routes work end-to-end; protected routes redirect to login.
- [ ] `useCurrentUser()` hook returns typed user info on the client.
- [ ] Logging out invalidates the session cookie and clears local TanStack Query cache.

## Technical notes
- Keep auth concerns out of the agent layer; pass `user_id` into use-cases via DI.
- Do not store GitHub OAuth scopes broader than `read:user` here — connector OAuth (with scopes for issues, code, etc.) is a separate flow handled in DEVHUB-025.

## Definition of done
- A new user can sign in, see an empty Threads page, and sign out.
