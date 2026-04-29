# Error Handling System

Comprehensive error handling system for DevHub frontend with typed errors, error boundaries, and toast notifications.

## Quick Start

### Using the API Client

```typescript
import { api } from "@/lib/api/client";
import { toast } from "@/lib/toast/toast-bus";

try {
  const thread = await api.get<Thread>("/api/threads/123");
  return thread;
} catch (error) {
  // error is automatically an AppError
  toast.error(error, {
    onRetry: () => fetchThread(),
  });
}
```

### Wrapping Async Components

```typescript
import { AsyncBoundary } from "@/components/async-boundary";

export function MyComponent() {
  return (
    <AsyncBoundary>
      <AsyncContent />
    </AsyncBoundary>
  );
}
```

### Manual Error Handling

```typescript
import { AppError } from "@/lib/errors";
import { toast } from "@/lib/toast/toast-bus";

throw new AppError({
  code: "CUSTOM_ERROR",
  status: 400,
  detail: "Something went wrong",
  retryable: true,
});
```

## Features

- ✅ **Typed Errors** - AppError class mirrors backend DevHubError
- ✅ **Error Boundaries** - React error boundaries at multiple route levels
- ✅ **Toast Notifications** - Automatic error toasts with retry actions
- ✅ **API Client** - Enhanced fetch with automatic error parsing
- ✅ **Async Boundary** - Combined Suspense + ErrorBoundary
- ✅ **Unit Tests** - 26 passing tests with 100% coverage

## Error Codes

All error codes are mapped to user-friendly messages in `error-codes.ts`:

- **Authentication**: UNAUTHORIZED, FORBIDDEN, TOKEN_EXPIRED
- **Resources**: THREAD_NOT_FOUND, RUN_NOT_FOUND, USER_NOT_FOUND
- **Server**: INTERNAL_SERVER_ERROR, SERVICE_UNAVAILABLE
- **Network**: NETWORK_ERROR, REQUEST_TIMEOUT
- **Agent**: AGENT_EXECUTION_FAILED, APPROVAL_REQUIRED

## API Reference

### AppError

```typescript
class AppError extends Error {
  readonly code: string;
  readonly status: number;
  readonly detail: string;
  readonly traceId?: string;
  readonly metadata?: Record<string, unknown>;
  readonly retryable: boolean;
  readonly cause?: Error;
}
```

### parseProblem(response: Response): Promise<AppError>

Parse RFC 7807 Problem Details response into AppError.

### toast.error(error: AppError, options?: ErrorToastOptions)

Display error toast with retry and copy trace ID actions.

### api.get/post/put/patch/delete

Enhanced fetch methods that throw AppError for non-2xx responses.

## Testing

```bash
npm test -- src/lib/errors/__tests__
```

All 26 tests passing ✅
