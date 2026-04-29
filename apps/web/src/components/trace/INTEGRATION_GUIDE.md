# Trace Viewer Integration Guide

## Quick Start

### 1. Import Components

```tsx
import { TraceDrawer } from "@/components/trace";
import { useTraceData } from "@/features/threads/hooks/use-trace-data";
```

### 2. Basic Usage

```tsx
function MessageComponent({ message }) {
  const { data: traceData, isLoading } = useTraceData(message.runId);

  if (isLoading || !traceData) return null;

  return (
    <div>
      <div>{message.content}</div>
      <TraceDrawer
        messageId={message.id}
        runId={message.runId}
        traceData={traceData}
      />
    </div>
  );
}
```

### 3. Custom Trigger

```tsx
<TraceDrawer
  messageId={messageId}
  runId={runId}
  traceData={traceData}
>
  <Button variant="outline" size="sm">
    <Activity className="h-4 w-4 mr-2" />
    Debug Trace
  </Button>
</TraceDrawer>
```

## Integration with Backend

### Backend API Endpoint

Implement the following endpoint in your backend:

```python
# FastAPI example
@router.get("/runs/{run_id}/trace")
async def get_run_trace(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> TraceResponse:
    """
    Get the complete execution trace for a run.
    
    Returns:
        TraceResponse with steps, duration, and status
    """
    # Fetch run events from database
    events = await get_run_events(session, run_id)
    
    # Transform events into trace steps
    steps = transform_events_to_trace(events)
    
    return TraceResponse(
        runId=run_id,
        steps=steps,
        totalDuration=calculate_total_duration(steps),
        status=get_run_status(run_id),
    )
```

### Data Transformation

Transform your backend events into the trace format:

```python
def transform_events_to_trace(events: List[RunEvent]) -> List[TraceStep]:
    """
    Transform run events into hierarchical trace steps.
    """
    steps = []
    event_stack = []  # Track nested events
    
    for event in events:
        if event.type == "agent_start":
            step = TraceStep(
                id=event.id,
                agentName=event.data.get("agent_name"),
                description=event.data.get("description"),
                status="running",
                startTime=event.timestamp,
                children=[],
            )
            
            if event_stack:
                # Add as child of current parent
                event_stack[-1].children.append(step)
            else:
                # Add as root step
                steps.append(step)
            
            event_stack.append(step)
        
        elif event.type == "tool_call":
            step = TraceStep(
                id=event.id,
                agentName=event_stack[-1].agentName if event_stack else None,
                toolName=event.data.get("tool_name"),
                args=event.data.get("args"),
                status="running",
                startTime=event.timestamp,
            )
            
            if event_stack:
                event_stack[-1].children.append(step)
            else:
                steps.append(step)
            
            event_stack.append(step)
        
        elif event.type == "tool_result":
            if event_stack:
                current_step = event_stack.pop()
                current_step.result = event.data.get("result")
                current_step.status = "success" if not event.data.get("error") else "error"
                current_step.error = event.data.get("error")
                current_step.endTime = event.timestamp
                current_step.duration = calculate_duration(
                    current_step.startTime,
                    current_step.endTime,
                )
        
        elif event.type == "agent_end":
            if event_stack:
                current_step = event_stack.pop()
                current_step.status = "success"
                current_step.endTime = event.timestamp
                current_step.duration = calculate_duration(
                    current_step.startTime,
                    current_step.endTime,
                )
    
    return steps
```

### Database Schema

Store trace-relevant data in your run_events table:

```sql
CREATE TABLE run_events (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL,
    sequence INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'agent_start', 'tool_call', 'tool_result', etc.
    data JSONB NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    parent_event_id UUID,  -- For nested events
    FOREIGN KEY (run_id) REFERENCES runs(id)
);

-- Index for efficient trace retrieval
CREATE INDEX idx_run_events_run_id_sequence ON run_events(run_id, sequence);
```

## Frontend Integration Points

### 1. Thread Detail View

Update `thread-detail.tsx` to include trace viewer:

```tsx
import { TraceDrawer } from "@/components/trace";
import { useTraceData } from "@/features/threads/hooks/use-trace-data";

function ThreadDetail({ threadId }) {
  const { messages } = useMessages(threadId);

  return (
    <div>
      {messages.map((message) => (
        <div key={message.id}>
          <StreamingMessage
            parts={message.parts}
            isStreaming={false}
            role={message.role}
            runId={message.runId}
            messageId={message.id}
            showTraceButton={true}
          />
        </div>
      ))}
    </div>
  );
}
```

### 2. Streaming Integration

The trace button automatically appears after streaming completes:

```tsx
<StreamingMessage
  parts={parts}
  isStreaming={isStreaming}
  role="assistant"
  runId={runId}  // Pass runId from streaming hook
  messageId={messageId}
  showTraceButton={true}  // Enable trace button
/>
```

### 3. Custom Trace Display

Use the `Trace` component directly without the drawer:

```tsx
import { Trace } from "@/components/trace";

function TracePanel({ runId }) {
  const { data: traceData } = useTraceData(runId);

  if (!traceData) return null;

  return (
    <div className="p-4">
      <h2>Execution Trace</h2>
      <Trace data={traceData} runId={runId} />
    </div>
  );
}
```

## LangSmith Integration

### 1. Generate LangSmith URL

In your backend, include LangSmith URL in the response:

```python
def get_langsmith_url(run_id: str) -> Optional[str]:
    """
    Generate LangSmith deep-link URL if available.
    """
    if not settings.LANGSMITH_PROJECT:
        return None
    
    return f"https://smith.langchain.com/o/{settings.LANGSMITH_ORG}/projects/p/{settings.LANGSMITH_PROJECT}/r/{run_id}"
```

### 2. Pass URL to TraceDrawer

```tsx
<TraceDrawer
  messageId={messageId}
  runId={runId}
  traceData={traceData}
  langsmithUrl={message.langsmithUrl}  // From backend
/>
```

## Performance Optimization

### 1. React Query Configuration

Optimize caching and refetching:

```tsx
import { QueryClient } from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,  // 30 seconds
      cacheTime: 300000,  // 5 minutes
      retry: 2,
    },
  },
});
```

### 2. Lazy Loading

Only fetch trace data when drawer is opened:

```tsx
function LazyTraceDrawer({ messageId, runId }) {
  const [open, setOpen] = useState(false);
  const { data: traceData } = useTraceData(open ? runId : null);

  return (
    <TraceDrawer
      messageId={messageId}
      runId={runId}
      traceData={traceData || { runId, steps: [], status: "running" }}
    />
  );
}
```

### 3. Virtualization

The trace component uses `react-virtuoso` for efficient rendering:

- Only visible items are rendered
- Smooth scrolling with dynamic heights
- Handles 200+ steps efficiently

## Troubleshooting

### Trace Data Not Loading

1. Check backend API endpoint is accessible
2. Verify runId is valid
3. Check browser console for errors
4. Verify React Query is configured

### Performance Issues

1. Check number of trace steps (should be < 200)
2. Verify virtualization is working
3. Check for unnecessary re-renders
4. Use React DevTools Profiler

### Styling Issues

1. Ensure Tailwind CSS is configured
2. Check dark mode theme provider
3. Verify shadcn/ui components are installed

## Testing

### Unit Tests

```tsx
import { render, screen } from "@testing-library/react";
import { Trace } from "@/components/trace";

describe("Trace", () => {
  it("renders trace steps", () => {
    const traceData = {
      runId: "run_123",
      steps: [
        {
          id: "step_1",
          agentName: "TestAgent",
          status: "success",
          duration: 100,
        },
      ],
      status: "completed",
    };

    render(<Trace data={traceData} runId="run_123" />);
    expect(screen.getByText("TestAgent")).toBeInTheDocument();
  });
});
```

### Integration Tests

```tsx
import { renderHook, waitFor } from "@testing-library/react";
import { useTraceData } from "@/features/threads/hooks/use-trace-data";

describe("useTraceData", () => {
  it("fetches trace data", async () => {
    const { result } = renderHook(() => useTraceData("run_123"));

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
    });

    expect(result.current.data?.runId).toBe("run_123");
  });
});
```

## Support

For questions or issues:
1. Check the README.md in `/apps/web/src/components/trace/`
2. Review the implementation summary in DEVHUB-022-IMPLEMENTATION.md
3. Contact the frontend team
