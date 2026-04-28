# [DEVHUB-018] App shell: sidebar, command bar, keyboard navigation

**Labels:** `epic:frontend-foundation` `area:web` `type:feature` `priority:P1`
**Estimate:** 3 pts
**Depends on:** DEVHUB-016, DEVHUB-005

## Story
**As a** user,
**I want** a Linear-grade app shell with a thread sidebar, command bar (`Cmd+K`), and keyboard shortcuts,
**so that** I can move around without my hands leaving the keyboard.

## Acceptance criteria
- [ ] Persistent left sidebar lists threads (paginated, virtualized if > 200).
- [ ] `Cmd+K` opens a command palette: new thread, switch agent, open settings, sign out.
- [ ] `Cmd+J` toggles theme; `Cmd+/` opens a shortcut cheat sheet.
- [ ] Mobile: sidebar collapses behind a sheet.
- [ ] Focus management: dialogs trap focus, restore focus on close.

## Definition of done
- Manual a11y pass (keyboard-only) navigates the entire app.
