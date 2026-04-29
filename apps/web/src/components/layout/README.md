# App Shell Layout Components

This directory contains the core layout components for the DevHub application shell.

## Components

### AppShell (`app-shell.tsx`)
The main application shell that wraps all authenticated pages.

**Features:**
- Responsive layout with desktop sidebar and mobile sheet
- Top navigation bar with user info
- Command palette trigger (Cmd+K)
- Keyboard shortcut integration

**Props:**
- `children`: React.ReactNode - Page content
- `user`: { name?: string | null; email?: string | null } - Current user info

### ThreadSidebar (`thread-sidebar.tsx`)
Persistent sidebar displaying thread list.

**Features:**
- Virtualized rendering for >200 threads (react-virtuoso)
- Regular scroll area for ≤200 threads
- New thread creation button
- Empty state with CTA
- Active thread highlighting
- Mobile-responsive with close callback

**Props:**
- `onThreadSelect?`: () => void - Callback when thread is selected (for mobile)

### CommandBar (`command-bar.tsx`)
Command palette (Cmd+K) for quick actions and navigation.

**Features:**
- Searchable command list
- Grouped commands (Actions, Navigation, Account)
- Keyboard shortcut hints
- Theme toggle (Cmd+J)
- Shortcuts dialog trigger (Cmd+/)

**Props:**
- `open`: boolean - Dialog open state
- `onOpenChange`: (open: boolean) => void - State change handler

### KeyboardShortcutsDialog (`keyboard-shortcuts-dialog.tsx`)
Comprehensive keyboard shortcuts cheat sheet (Cmd+/).

**Features:**
- Categorized shortcuts (General, Navigation, Accessibility)
- Visual keyboard key representations
- Responsive layout

**Props:**
- `open`: boolean - Dialog open state
- `onOpenChange`: (open: boolean) => void - State change handler

## Usage

```tsx
import { AppShell } from "@/components/layout/app-shell";

export default async function AppLayout({ children }) {
  const session = await auth();
  
  return (
    <AppShell user={session.user}>
      {children}
    </AppShell>
  );
}
```

## Keyboard Shortcuts

- **Cmd+K / Ctrl+K**: Open command palette
- **Cmd+J / Ctrl+J**: Toggle theme
- **Cmd+/ / Ctrl+/**: Show keyboard shortcuts
- **Cmd+N / Ctrl+N**: New thread
- **Esc**: Close dialogs
- **Tab / Shift+Tab**: Navigate focus

## Accessibility

- Full keyboard navigation support
- Focus trapping in dialogs
- Focus restoration on close
- ARIA labels on interactive elements
- Screen reader announcements
- Semantic HTML structure

## Dependencies

- `cmdk`: Command palette library
- `react-virtuoso`: Virtualized list rendering
- `@radix-ui/react-dialog`: Dialog primitives
- `lucide-react`: Icon library
- `next-themes`: Theme management
- `@tanstack/react-query`: Data fetching
