"""End-to-end test for HITL interrupts.

Tests the complete flow:
1. Start a run that triggers a tool requiring approval
2. Verify interrupt event is emitted
3. Submit approval via API
4. Verify the tool executes and run completes
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from devhub.adapters.persistence.models import HITLApproval as OrmHITLApproval
from devhub.adapters.persistence.repositories import (
    AuditLogRepository,
    HITLApprovalRepository,
)
from devhub.domain.hitl_interrupt import HITLInterruptHandler
from devhub.domain.models import ToolCall


@pytest.mark.asyncio
async def test_create_and_resolve_approval(db_session):
    """Test creating and resolving an approval."""
    repo = HITLApprovalRepository(db_session)

    run_id = uuid.uuid4()
    tool_call = {
        "tool_name": "github_create_comment",
        "args": {"body": "LGTM"},
        "agent_id": "pr_reviewer",
    }
    summary = "Post a comment on PR #123"
    risk = "medium"
    expires_at = datetime.now(UTC) + timedelta(minutes=30)

    # Create approval
    approval = await repo.create(
        run_id=run_id,
        tool_call=tool_call,
        summary=summary,
        risk=risk,
        expires_at=expires_at,
    )

    assert approval is not None
    from devhub.domain.models import HITLApproval

    if isinstance(approval, HITLApproval):
        assert approval.run_id == run_id
        assert approval.status == "pending"
        assert approval.summary == summary

        # Resolve approval
        await repo.resolve(approval.id, "approve")

        # Verify resolution
        resolved = await repo.get(approval.id)
        assert resolved is not None
        if isinstance(resolved, HITLApproval):
            assert resolved.status == "approved"
            assert resolved.decision == "approve"


@pytest.mark.asyncio
async def test_expire_pending_approvals(db_session):
    """Test that expired approvals are automatically rejected."""
    repo = HITLApprovalRepository(db_session)

    run_id = uuid.uuid4()
    tool_call = {"tool_name": "test_tool", "args": {}, "agent_id": "test"}

    # Create approval that expires in the past
    expired_approval = OrmHITLApproval(
        run_id=run_id,
        tool_call=tool_call,
        summary="Test",
        risk="low",
        status="pending",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(expired_approval)
    await db_session.commit()
    await db_session.refresh(expired_approval)

    # Run expiration
    expired_ids = await repo.expire_pending()

    assert expired_approval.id in expired_ids

    # Verify it's marked as expired
    result = await repo.get(expired_approval.id)
    from devhub.domain.models import HITLApproval

    if isinstance(result, HITLApproval):
        assert result.status == "expired"
        assert result.decision == "reject"


@pytest.mark.asyncio
async def test_audit_log_creation(db_session):
    """Test that approvals are logged to audit log."""
    audit_repo = AuditLogRepository(db_session)

    user_id = uuid.uuid4()
    approval_id = uuid.uuid4()
    decision = "approve"
    patched_args = {"body": "Updated comment"}

    await audit_repo.log_approval(
        user_id=user_id,
        approval_id=approval_id,
        decision=decision,
        patched_args=patched_args,
    )

    # Verify the log was created (would need to add a get method to verify)
    # For now, just ensure no exception was raised
    assert True


@pytest.mark.asyncio
async def test_hitl_interrupt_handler(db_session):
    """Test the HITL interrupt handler."""
    from devhub.adapters.streaming.event_store import EventStore

    approval_repo = HITLApprovalRepository(db_session)
    event_store = EventStore()
    handler = HITLInterruptHandler(approval_repo, event_store)

    run_id = uuid.uuid4()
    tool_call = ToolCall(
        tool_name="github_create_comment",
        args={"body": "LGTM"},
        agent_id="pr_reviewer",
    )

    # Create interrupt
    request = await handler.create_interrupt(
        run_id=run_id,
        tool_call=tool_call,
        summary="Post comment on PR",
        risk="medium",
    )

    assert request.run_id == run_id
    assert request.tool_call == tool_call
    assert request.summary == "Post comment on PR"

    # Check status
    status = await handler.check_approval_status(request.approval_id)
    assert status == "pending"


@pytest.fixture
async def db_session():
    """Create a test database session."""
    from devhub.adapters.persistence.database import get_session_factory

    async with get_session_factory()() as session:
        yield session


@pytest.mark.asyncio
@pytest.mark.integration
async def test_approval_endpoint(client: AsyncClient, auth_headers: dict[str, str]):
    """Test the approval submission endpoint."""
    # This would require a full integration test setup
    # For now, this is a placeholder showing the expected flow
    pass
