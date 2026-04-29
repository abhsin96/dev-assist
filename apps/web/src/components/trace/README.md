# Trace Viewer Components

Comprehensive trace viewer for debugging agent execution in DevHub.

## Components

### TraceDrawer

Drawer component that opens from assistant messages to show the full agent trace.

```tsx
import { TraceDrawer } from "@/components/trace";

<TraceDrawer
  messageId="msg_123"
  runId="run_456"
  traceData={traceData}
  langsmithUrl="https://smith.langchain.com/..."
/>
```

### Trace

Main trace tree component with virtualization for performance.

```tsx
import { Trace } from "@/components/trace";

<Trace data={traceData} runId="run_456" />
```

### Compound Components

The trace viewer uses compound components for flexibility:

- `<Trace.Step>` - Individual trace step
- `<Trace.Tool>` - Tool call details (args/result)
- `<Trace.Error>` - Error details with stack trace

## Features

### Virtualization

Uses `react-virtuoso` for efficient rendering of large traces (up to 200+ steps).

### Expandable Tree

- Click steps to expand/collapse children
- Click step header to show/hide details (args, result, metadata)
- Nested indentation shows hierarchy

### Status Indicators

- ✓ Success (green)
- ⚠ Error (red)
- ⏱ Pending/Running (gray)

### Performance Stats

- Total steps count
- Total duration
- Error count

### Deep Linking

Optional LangSmith integration for users with access.

## Type Definitions

```typescript
interface TraceStep {
  id: string;
  agentName?: string;
  toolName?: string;
  description?: string;
  args?: Record<string, unknown>;
  result?: unknown;
  error?: string | Error | Record<string, unknown>;
  status: "pending" | "running" | "success" | "error";
  duration?: number; // milliseconds
  startTime?: string;
  endTime?: string;
  metadata?: Record<string, unknown>;
  children?: TraceStep[];
}

interface TraceData {
  runId: string;
  steps: TraceStep[];
  totalDuration?: number;
  status: "running" | "completed" | "failed";
}
```

## Usage Example

```tsx
import { TraceDrawer } from "@/components/trace";
import { Button } from "@/components/ui/button";
import { Activity } from "lucide-react";

function MessageWithTrace({ message, traceData }) {
  return (
    <div>
      <div>{message.content}</div>
      <TraceDrawer
        messageId={message.id}
        runId={message.runId}
        traceData={traceData}
        langsmithUrl={message.langsmithUrl}
      >
        <Button variant="ghost" size="sm">
          <Activity className="h-4 w-4" />
          View trace
        </Button>
      </TraceDrawer>
    </div>
  );
}
```

## Performance

- Virtualized rendering for traces with 200+ steps
- Renders under 100ms for large traces
- Lazy loading of step details
- Efficient expand/collapse state management

## Accessibility

- Keyboard navigation support
- ARIA labels for screen readers
- Focus management in drawer
- Semantic HTML structure
