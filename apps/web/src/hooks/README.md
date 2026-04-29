# Global Hooks

## Overview

This directory contains global React hooks used across the application.

## Hooks

### `use-auto-scroll.ts`

Manages auto-scroll behavior with manual scroll detection.

**Options:**

```typescript
interface UseAutoScrollOptions {
  isStreaming: boolean;  // Whether content is streaming
  threshold?: number;    // Pixels from bottom to consider "at bottom" (default: 100)
}
```

**Return Value:**

```typescript
interface UseAutoScrollReturn<T> {
  containerRef: RefObject<T>;      // Ref for scroll container
  isAtBottom: boolean;             // Whether user is at bottom
  showJumpToLatest: boolean;       // Whether to show jump pill
  scrollToBottom: (smooth?: boolean) => void;  // Scroll to bottom function
}
```

**Usage:**

```typescript
import { useAutoScroll } from '@/hooks/use-auto-scroll';

const { containerRef, showJumpToLatest, scrollToBottom } = useAutoScroll({
  isStreaming,
  threshold: 100,
});

<div ref={containerRef} className="overflow-y-auto">
  {/* Content */}
</div>

<JumpToLatest
  show={showJumpToLatest}
  onClick={() => scrollToBottom()}
/>
```

**Features:**

- Detects when user is at bottom
- Disables auto-scroll when user scrolls up
- Shows jump pill when scrolled up during streaming
- Debounced scroll event handling (100ms)
- Automatic cleanup

**Behavior:**

1. **Auto-Scroll:** Enabled when user is at bottom and content is streaming
2. **Manual Scroll:** Detected when user scrolls up
3. **Jump Pill:** Shown when user scrolls up during streaming
4. **Resume:** Auto-scroll resumes when user returns to bottom

### `use-keyboard-shortcuts.ts`

Manages global keyboard shortcuts.

## Best Practices

1. **Refs:** Always attach `containerRef` to the scrollable container
2. **Threshold:** Adjust threshold based on your UI (default 100px works well)
3. **Smooth Scroll:** Use `scrollToBottom(true)` for user-initiated scrolls
4. **Instant Scroll:** Use `scrollToBottom(false)` during streaming
