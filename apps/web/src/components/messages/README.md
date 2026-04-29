# Message Components

## Overview

This directory contains components for rendering streaming messages with different part types.

## Components

### `streaming-message.tsx`

Main component for rendering streaming messages with support for text, tool calls, tool results, errors, and interrupts.

**Props:**

```typescript
interface StreamingMessageProps {
  parts: MessagePart[];      // Message parts to render
  isStreaming: boolean;      // Whether message is currently streaming
  role: 'user' | 'assistant'; // Message role
  className?: string;        // Additional CSS classes
}
```

**Message Part Types:**

1. **Text:** Rendered with ReactMarkdown + GFM
2. **Tool Call:** Blue card with tool name and arguments
3. **Tool Result:** Green/red card with result or error
4. **Error:** Red card with error message
5. **Interrupt:** Amber card for HITL approvals
6. **State:** Gray card with agent information

**Usage:**

```typescript
import { StreamingMessage } from '@/components/messages/streaming-message';

<StreamingMessage
  parts={parts}
  isStreaming={isStreaming}
  role="assistant"
/>
```

### `jump-to-latest.tsx`

Floating pill for jumping to latest message when user scrolls up.

**Props:**

```typescript
interface JumpToLatestProps {
  show: boolean;           // Whether to show the pill
  onClick: () => void;     // Click handler
  className?: string;      // Additional CSS classes
}
```

**Usage:**

```typescript
import { JumpToLatest } from '@/components/messages/jump-to-latest';

<JumpToLatest
  show={showJumpToLatest}
  onClick={() => scrollToBottom()}
/>
```

## Styling

All components use Tailwind CSS with dark mode support:

- **Text:** Prose styling with `prose-sm dark:prose-invert`
- **Tool Call:** Blue theme (`blue-50`, `blue-600`, etc.)
- **Tool Result:** Green for success, red for failure
- **Error:** Red theme
- **Interrupt:** Amber theme
- **State:** Gray theme

## Accessibility

- Semantic HTML structure
- Proper color contrast
- Keyboard navigation
- Screen reader friendly
