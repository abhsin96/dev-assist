"""HITL interrupt handler for LangGraph integration.

This module provides the interrupt mechanism that pauses graph execution
when a tool with requires_approval=True is about to run.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.tools import BaseTool

from devhub.domain.models import HITLRequest, RiskLevel, ToolCall

if TYPE_CHECKING:
    from devhub.adapters.streaming.event_store import EventStore
    from devhub.domain.ports import IHITLApprovalRepository


class HITLInterruptHandler:
    """Handles HITL interrupts for tools requiring approval."""

    def __init__(
        self,
        approval_repo: IHITLApprovalRepository,
        event_store: EventStore,
    ) -> None:
        self._approval_repo = approval_repo
        self._event_store = event_store

    async def should_interrupt(self, tool: BaseTool) -> bool:
        """Check if a tool requires approval."""
        return getattr(tool, "requires_approval", False)

    async def create_interrupt(
        self,
        run_id: uuid.UUID,
        tool_call: ToolCall,
        *,
        summary: str | None = None,
        risk: RiskLevel = "medium",
        ttl_minutes: int = 30,
    ) -> HITLRequest:
        """Create an interrupt request and persist it.

        Args:
            run_id: The run ID this interrupt belongs to
            tool_call: The tool call requiring approval
            summary: Human-readable summary of the action
            risk: Risk level (low, medium, high)
            ttl_minutes: Time to live in minutes before auto-reject

        Returns:
            HITLRequest that was created and persisted
        """
        approval_id = uuid.uuid4()
        expires_at = datetime.now(UTC) + timedelta(minutes=ttl_minutes)

        # Generate summary if not provided
        if summary is None:
            summary = self._generate_summary(tool_call)

        # Persist the approval request
        await self._approval_repo.create(
            run_id=run_id,
            tool_call={
                "tool_name": tool_call.tool_name,
                "args": tool_call.args,
                "agent_id": tool_call.agent_id,
            },
            summary=summary,
            risk=risk,
            expires_at=expires_at,
        )

        # Create the request object
        request = HITLRequest(
            approval_id=approval_id,
            run_id=run_id,
            tool_call=tool_call,
            summary=summary,
            risk=risk,
            expires_at=expires_at,
        )

        # Emit interrupt event to stream
        from devhub.application.use_cases.run_events import InterruptEvent

        await self._event_store.publish(
            run_id,
            InterruptEvent(
                approval_id=str(approval_id),
                run_id=str(run_id),
                tool_call={
                    "tool_name": tool_call.tool_name,
                    "args": tool_call.args,
                    "agent_id": tool_call.agent_id,
                },
                summary=summary,
                risk=risk,
                expires_at=expires_at.isoformat(),
            ),
        )

        return request

    def _generate_summary(self, tool_call: ToolCall) -> str:
        """Generate a human-readable summary of the tool call."""
        action_verbs = {
            "github_create_comment": "post a comment",
            "github_close_issue": "close an issue",
            "github_create_pr": "create a pull request",
            "confluence_create_page": "create a Confluence page",
            "confluence_update_page": "update a Confluence page",
            "jira_create_issue": "create a Jira issue",
            "jira_update_issue": "update a Jira issue",
        }

        verb = action_verbs.get(tool_call.tool_name, f"execute {tool_call.tool_name}")
        return f"Agent {tool_call.agent_id} wants to {verb}"

    async def check_approval_status(self, approval_id: uuid.UUID) -> str:
        """Check the status of an approval request.

        Returns:
            Status: 'pending', 'approved', 'rejected', or 'expired'
        """
        from devhub.domain.models import HITLApproval

        approval = await self._approval_repo.get(approval_id)
        if approval is None:
            return "not_found"

        if isinstance(approval, HITLApproval):
            return approval.status

        return "unknown"

    async def get_approved_args(self, approval_id: uuid.UUID) -> dict[str, Any] | None:
        """Get the approved (possibly patched) arguments for a tool call.

        Returns:
            The patched args if provided, otherwise the original args, or None if rejected
        """
        from devhub.domain.models import HITLApproval

        approval = await self._approval_repo.get(approval_id)
        if approval is None or not isinstance(approval, HITLApproval):
            return None

        if approval.status == "rejected" or approval.status == "expired":
            return None

        # Return patched args if provided, otherwise original args
        if approval.patched_args:
            return approval.patched_args

        return approval.tool_call.get("args")
