# HITL Interrupts Implementation

## Overview

This implementation adds Human-in-the-Loop (HITL) interrupt functionality to DevHub, allowing the system to pause and request user approval before executing destructive or sensitive actions.

## Architecture

### Components

1. **Database Layer** (`persistence/models.py`)
   - `HITLApproval`: Stores approval requests with status, expiration, and resolution data
   - `AuditLog`: Records all approval decisions for compliance and auditing

2. **Domain Models** (`domain/models.py`)
   - `HITLRequest`: Value object representing an approval request
   - `ApprovalSubmission`: Input model for approval/rejection
   - `HITLApproval`: Domain model for approval state
   - `AuditLogEntry`: Domain model for audit records

3. **Repositories** (`persistence/repositories.py`)
   - `HITLApprovalRepository`: CRUD operations for approvals
   - `AuditLogRepository`: Logging approval decisions

4. **Interrupt Handler** (`domain/hitl_interrupt.py`)
   - `HITLInterruptHandler`: Core logic for creating interrupts, checking status, and managing approval flow

5. **Background Tasks** (`application/use_cases/expire_approvals.py`)
   - `ExpireApprovalsTask`: Periodically expires pending approvals past their TTL

6. **API Endpoints** (`api/routers/runs.py`)
   - `POST /runs/{run_id}/approvals`: Submit approval/rejection decisions

### Integration with LangGraph

The HITL interrupt system integrates with LangGraph through:

1. **Tool Wrapper**: `MCPToolWrapper` checks `requires_approval` attribute
2. **Interrupt Invocation**: Before executing a tool with `requires_approval=True`, the system:
   - Creates an `HITLRequest` via `HITLInterruptHandler`
   - Persists the approval to the database
   - Emits an `InterruptEvent` to the SSE stream
   - Calls `interrupt()` to pause the graph

3. **Resume Flow**: When approval is submitted:
   - API endpoint validates and resolves the approval
   - Logs to audit trail
   - LangGraph resumes execution with approved (or patched) arguments

## Usage

### Marking Tools as Requiring Approval

Tools are marked for approval in two ways:

1. **Explicit**: Pass `requires_approval=True` when creating `MCPToolWrapper`
2. **Automatic**: Tools with `readOnlyHint=False` in MCP annotations are auto-flagged

### Approval Flow

1. User starts a run that triggers a tool requiring approval
2. System emits `InterruptEvent` via SSE:
   ```json
   {
     "event": "interrupt",
     "data": {
       "approval_id": "uuid",
       "run_id": "uuid",
       "tool_call": {...},
       "summary": "Agent pr_reviewer wants to post a comment",
       "risk": "medium",
       "expires_at": "2024-01-01T12:30:00Z"
     }
   }
   ```

3. User submits decision:
   ```bash
   POST /runs/{run_id}/approvals
   {
     "approval_id": "uuid",
     "decision": "approve",
     "patched_args": {"body": "Modified comment"}  # optional
   }
   ```

4. System resumes the run with approved arguments

### Rejection Handling

When a user rejects an approval:
- The agent is informed of the rejection
- The agent should propose an alternative action or stop
- The run continues (doesn't fail automatically)

### Expiration

Approvals expire after 30 minutes (configurable) by default:
- Background task runs every 60 seconds
- Expired approvals are auto-rejected
- Agent is notified of expiration

## Database Schema

```sql
-- HITL approvals
CREATE TABLE hitl_approvals (
    id          UUID PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES runs(id),
    tool_call   JSONB NOT NULL,
    summary     TEXT NOT NULL,
    risk        TEXT NOT NULL DEFAULT 'medium',
    status      TEXT NOT NULL DEFAULT 'pending',
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    decision    TEXT,
    patched_args JSONB
);

-- Audit log
CREATE TABLE audit_log (
    id          UUID PRIMARY KEY,
    user_id     UUID NOT NULL REFERENCES users(id),
    approval_id UUID NOT NULL REFERENCES hitl_approvals(id),
    decision    TEXT NOT NULL,
    patched_args JSONB,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Testing

Run the test suite:

```bash
pytest tests/test_hitl_interrupts.py -v
```

Tests cover:
- Approval creation and resolution
- Automatic expiration
- Audit logging
- Interrupt handler functionality
- End-to-end approval flow

## Configuration

- **Expiration TTL**: Default 30 minutes, configurable per interrupt
- **Expiration Check Interval**: 60 seconds (configurable in `main.py`)
- **Risk Levels**: `low`, `medium`, `high`

## Future Enhancements

- [ ] Add approval delegation (allow specific users to approve)
- [ ] Implement approval policies (auto-approve low-risk actions)
- [ ] Add approval history UI
- [ ] Support bulk approvals
- [ ] Add approval notifications (email, Slack, etc.)
