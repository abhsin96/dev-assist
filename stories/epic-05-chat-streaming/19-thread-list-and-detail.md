# [DEVHUB-019] Thread list & thread detail pages

**Labels:** `epic:chat-streaming` `area:web` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-018, DEVHUB-008

## Story
**As a** user,
**I want** to create, list, rename, and delete threads,
**so that** my conversations are persistent and organized.

## Acceptance criteria
- [ ] `app/(chat)/threads/page.tsx` (RSC) lists threads with title, last message snippet, updated time.
- [ ] `app/(chat)/threads/[id]/page.tsx` renders message history server-side, then hands off to a client island for streaming.
- [ ] Inline rename via double-click; soft-delete with undo toast.
- [ ] TanStack Query manages the client-side cache; mutations optimistically update the sidebar.
- [ ] Empty state with CTA to start a thread.
- [ ] Backend endpoints `GET/POST/PATCH/DELETE /threads[...]` exist (covered by DEVHUB-006/008 use-cases).

## Definition of done
- Create, rename, delete, and reopen a thread; data round-trips through the API.
