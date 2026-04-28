# [DEVHUB-016] Next.js 15 + shadcn/ui + design tokens

**Labels:** `epic:frontend-foundation` `area:web` `type:feature` `priority:P0`
**Estimate:** 3 pts
**Depends on:** DEVHUB-001

## Story
**As a** frontend developer,
**I want** Next.js 15 (App Router, React 19), Tailwind v4, and shadcn/ui set up with our design tokens and dark mode,
**so that** every later UI story starts from a polished baseline.

## Acceptance criteria
- [ ] App Router enabled; `app/layout.tsx` sets fonts (Geist), color tokens, and `<ThemeProvider>` (system / light / dark).
- [ ] shadcn/ui initialized; baseline components installed: `button`, `input`, `dialog`, `dropdown-menu`, `tooltip`, `sonner`, `tabs`, `card`, `scroll-area`.
- [ ] Tailwind config consumes a tokens file (`styles/tokens.css`) — no inline color literals in components.
- [ ] Lighthouse a11y score ≥ 95 on the empty home page.
- [ ] Storybook (or a `/_dev/components` page) demos every primitive in light/dark.
- [ ] `next.config.ts` has `typedRoutes: true` and `experimental.reactCompiler: true`.

## Definition of done
- A new contributor can build a page using only shadcn primitives and tokens, with no custom CSS.
