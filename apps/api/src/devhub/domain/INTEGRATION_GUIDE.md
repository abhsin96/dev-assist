# HITL Interrupts - LangGraph Integration Guide

## Overview

This guide explains how to integrate HITL (Human-in-the-Loop) interrupts into the LangGraph execution flow.

## Integration Points

### 1. Tool Execution Interception

The HITL interrupt system intercepts tool execution at the `MCPToolWrapper._arun()` method. Here's how to integrate:

```python
# In MCPToolWrapper._arun() method
async def _arun(self, **kwargs: Any) -> str:
    # Check if this tool requires approval
    if self.requires_approval:
        # Get the interrupt handler from context
        # (passed via graph config or dependency injection)
        handler = self._get_interrupt_handler()
        
        # Create the tool call object
        tool_call = ToolCall(
            tool_name=self.name,
            args=kwargs,
            agent_id=self.agent_id,
        )
        
        # Create interrupt and wait for approval
        run_id = self._get_run_id_from_context()
        request = await handler.create_interrupt(
            run_id=run_id,
            tool_call=tool_call,
            risk=self._assess_risk(tool_call),
        )
        
        # Invoke LangGraph interrupt
        from langgraph.types import interrupt
        
        # This pauses the graph and returns control to the caller
        approval_result = interrupt(
            {
                "approval_id": str(request.approval_id),
                "message": request.summary,
            }
        )
        
        # When resumed, check if approved
        status = await handler.check_approval_status(request.approval_id)
        
        if status in ["rejected", "expired"]:
            raise RuntimeError(
                f"Action was {status} by user. Please propose an alternative."
            )
        
        # Get approved (possibly patched) arguments
        approved_args = await handler.get_approved_args(request.approval_id)
        if approved_args:
            kwargs = approved_args
    
    # Execute the tool with approved arguments
    result = await self._call_fn(
        ToolCall(
            tool_name=self.name,
            args=kwargs,
            agent_id=self.agent_id,
        )
    )
    
    if not result.ok:
        raise RuntimeError(result.error or "MCP tool call failed")
    
    return str(result.data)
```

### 2. Graph Configuration

Pass the interrupt handler to the graph via configuration:

```python
# In main.py or graph compilation
from devhub.domain.hitl_interrupt import HITLInterruptHandler

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # ... existing setup ...
    
    # Create interrupt handler
    async with get_session_factory()() as session:
        approval_repo = HITLApprovalRepository(session)
        event_store = EventStore()
        interrupt_handler = HITLInterruptHandler(approval_repo, event_store)
        
        # Store in app state for access during graph execution
        app.state.interrupt_handler = interrupt_handler
    
    # Compile graph with interrupt support
    llm = AnthropicLLMClient(api_key=settings.anthropic_api_key)
    app.state.graph = compile_supervisor_graph(
        llm, 
        MemorySaver(),
        interrupt_handler=interrupt_handler,  # Pass to graph
    )
```

### 3. Resume Endpoint Enhancement

The approval endpoint needs to resume the graph after approval:

```python
@router.post("/runs/{run_id}/approvals", status_code=200)
async def submit_approval(
    run_id: uuid.UUID,
    body: ApprovalSubmission,
    user: CurrentUser,
    approval_repo: Annotated[IHITLApprovalRepository, Depends(get_hitl_approval_repo)],
    audit_repo: Annotated[IAuditLogRepository, Depends(get_audit_log_repo)],
    graph: Annotated[Any, Depends(get_graph)],
) -> dict[str, str]:
    user_id = uuid.UUID(str(user["sub"]))
    
    # Resolve approval
    await approval_repo.resolve(
        body.approval_id, 
        body.decision, 
        body.patched_args
    )
    
    # Log to audit
    await audit_repo.log_approval(
        user_id, 
        body.approval_id, 
        body.decision, 
        body.patched_args
    )
    
    # Resume the graph
    # LangGraph will automatically resume from the interrupt point
    # The interrupt() call will return with the approval data
    config = {
        "configurable": {
            "thread_id": str(run_id),
            "approval_id": str(body.approval_id),
            "decision": body.decision,
            "patched_args": body.patched_args,
        }
    }
    
    # Graph will resume automatically when next accessed
    # No explicit resume call needed - LangGraph handles this
    
    return {"status": "ok", "decision": body.decision}
```

### 4. Handling Rejections in Agents

Agents must handle rejection gracefully:

```python
# In specialist agent nodes (e.g., pr_reviewer.py)
async def pr_reviewer_node(state: AgentState) -> Command[str]:
    try:
        # ... agent logic ...
        
        # When tool execution fails due to rejection
        result = await tool.ainvoke(args)
        
    except RuntimeError as exc:
        if "rejected" in str(exc) or "expired" in str(exc):
            # User rejected the action
            rejection_msg = AIMessage(
                content="I understand you don't want me to proceed with that action. "
                        "Would you like me to suggest an alternative approach?"
            )
            return Command(
                goto="supervisor",
                update={
                    "messages": [rejection_msg],
                    "current_agent": "supervisor",
                },
            )
        raise
```

## Configuration in Graph Builder

Update the graph builder to accept and propagate the interrupt handler:

```python
def build_supervisor_graph(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None = None,
    vector_store: IVectorStore | None = None,
    interrupt_handler: HITLInterruptHandler | None = None,
) -> StateGraph:
    """Build supervisor graph with HITL interrupt support."""
    
    builder: StateGraph[AgentState] = StateGraph(AgentState)
    
    # Pass interrupt_handler to specialist nodes
    builder.add_node(
        "pr_reviewer",
        make_pr_reviewer_node(
            llm, 
            mcp_registry, 
            interrupt_handler=interrupt_handler
        ),
    )
    
    # ... other nodes ...
    
    return builder
```

## MCP Registry Integration

Update the MCP registry to inject the interrupt handler into tools:

```python
# In MCPRegistry.tools_for() method
async def tools_for(self, agent_id: str) -> list[BaseTool]:
    tools = []
    
    for server_id in self._get_allowed_servers(agent_id):
        mcp_tools = await self._get_tools_from_server(server_id)
        
        for mcp_tool in mcp_tools:
            wrapper = MCPToolWrapper(
                mcp_tool=mcp_tool,
                server_id=server_id,
                agent_id=agent_id,
                call_fn=self.call,
                requires_approval=self._should_require_approval(mcp_tool),
            )
            
            # Inject interrupt handler
            if self._interrupt_handler:
                wrapper.set_interrupt_handler(self._interrupt_handler)
            
            tools.append(wrapper)
    
    return tools
```

## Testing the Integration

### Manual Test Flow

1. Start a run that triggers a tool requiring approval:
   ```bash
   POST /threads/{thread_id}/runs
   {"message": "Review PR #123 and post a comment"}
   ```

2. Monitor SSE stream for interrupt event:
   ```bash
   GET /runs/{run_id}/events
   ```

3. Submit approval:
   ```bash
   POST /runs/{run_id}/approvals
   {
     "approval_id": "<from interrupt event>",
     "decision": "approve"
   }
   ```

4. Verify the tool executes and run completes

### Automated E2E Test

See `tests/test_hitl_interrupts.py` for the complete test suite.

## Troubleshooting

### Graph doesn't pause
- Verify `requires_approval=True` is set on the tool
- Check that `interrupt()` is being called
- Ensure the graph is compiled with a checkpointer

### Resume doesn't work
- Verify the `thread_id` in config matches the run
- Check that approval was resolved in database
- Ensure graph has access to updated config

### Events not emitted
- Verify EventStore is properly initialized
- Check that interrupt handler has access to event store
- Ensure SSE connection is active

## Performance Considerations

- **Database connections**: Each interrupt creates a DB transaction
- **Expiration checks**: Run every 60 seconds by default (configurable)
- **Event store**: In-memory by default; consider Redis for production
- **Checkpointer**: MemorySaver is for development only; use PostgreSQL for production

## Security Considerations

- **Authorization**: Verify user owns the run before accepting approval
- **Audit trail**: All approvals are logged with user ID and timestamp
- **Expiration**: Prevents indefinite pending states
- **Argument patching**: Validate patched args before execution
