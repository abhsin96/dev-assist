# Thread Hooks

## Overview

This directory contains React hooks for managing thread-related functionality.

## Hooks

### `use-streaming-message.ts`

Manages streaming message state and SSE connection.

**Options:**

```typescript
interface UseStreamingMessageOptions {
  threadId: string;                      // Thread ID
  onComplete?: (parts: MessagePart[]) => void;  // Completion callback
  onError?: (error: Error) => void;      // Error callback
}
```

**Return Value:**

```typescript
interface UseStreamingMessageReturn {
  parts: MessagePart[];        // Current message parts
  isStreaming: boolean;        // Streaming status
  error: Error | null;         // Error state
  startStream: (runId: string) => Promise<void>;  // Start streaming
  cancelStream: () => void;    // Cancel stream
  retry: () => void;           // Retry failed stream
}
```

**Usage:**

```typescript
import { useStreamingMessage } from '@/features/threads/hooks/use-streaming-message';

const {
  parts,
  isStreaming,
  error,
  startStream,
  cancelStream,
  retry,
} = useStreamingMessage({
  threadId: 'thread-123',
  onComplete: (parts) => console.log('Completed:', parts),
  onError: (error) => console.error('Error:', error),
});

// Start streaming
await startStream('run-456');

// Cancel if needed
cancelStream();

// Retry on error
if (error) {
  retry();
}
```

**Features:**

- Automatic cleanup on unmount
- AbortController integration
- Toast notifications
- Error handling with retry
- Text accumulation optimization

### `use-threads.ts`

Manages thread list with React Query.

### `use-thread-mutations.ts`

Manages thread CRUD mutations.

## Best Practices

1. **Cleanup:** All hooks handle cleanup automatically
2. **Error Handling:** Always handle errors with `onError` callback
3. **Cancellation:** Use `cancelStream` when component unmounts or user navigates away
4. **Retry:** Provide retry functionality for failed streams
