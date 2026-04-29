# Streaming Infrastructure

## Overview

This directory contains the SSE (Server-Sent Events) transport adapter that bridges the backend's streaming protocol with the Vercel AI SDK.

## Files

### `sseTransport.ts`

Adapts the backend's SSE protocol to the Vercel AI SDK `Transport` interface.

**Key Features:**
- Parses SSE event stream from backend
- Converts backend events to AI SDK stream parts
- Handles reconnection with `from=<seq>` resume capability
- Supports AbortController for cancellation

**Usage:**

```typescript
import { createSSETransport } from '@/lib/streaming/sseTransport';

const stream = await createSSETransport({
  url: '/api/runs/stream',
  runId: 'run-123',
  fromSeq: 0,
  signal: abortController.signal,
  onError: (error) => console.error(error),
  onReconnect: (fromSeq) => console.log(`Reconnecting from ${fromSeq}`),
});

for await (const part of stream) {
  console.log(part);
}
```

## Event Type Mapping

| Backend Event | AI SDK Stream Part | Description |
|--------------|-------------------|-------------|
| `token` | `text-delta` | Text token from LLM |
| `tool_call` | `tool-call` | Tool invocation |
| `tool_result` | `tool-result` | Tool execution result |
| `error` | `error` | Error during execution |
| `done` | `finish` | Stream completed |
| `state` | N/A | Agent state (handled in UI) |
| `interrupt` | N/A | HITL interrupt (handled in UI) |
| `heartbeat` | N/A | Keep-alive (ignored) |

## Reconnection Logic

The transport implements automatic reconnection with exponential backoff:

1. **Max Attempts:** 3
2. **Backoff:** 1s, 2s, 3s
3. **Resume:** Uses `from=<seq>` parameter to resume from last sequence
4. **Notification:** Calls `onReconnect` callback on reconnection

## Error Handling

- **Network Errors:** Automatically retries with backoff
- **HTTP Errors:** Throws error after max retries
- **Parse Errors:** Logs warning and continues
- **Cancellation:** Respects AbortController signal

## Testing

Test the transport with slow network conditions:

```bash
# Enable Chrome DevTools Network throttling (Slow 3G)
# Send a message and verify:
# - Stream remains responsive
# - Reconnection works
# - No stuck UI states
```
