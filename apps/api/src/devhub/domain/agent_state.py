"""Shared graph state for all LangGraph runs.

Matches ARCHITECTURE.md §3 exactly. Every field that accumulates uses a
reducer so LangGraph can merge partial updates from parallel nodes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

AgentName = Literal["supervisor", "echo_specialist"]


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    agent: AgentName
    status: Literal["pending", "running", "done", "failed"] = "pending"


@dataclass(frozen=True)
class AgentErrorRecord:
    code: str
    message: str
    agent: AgentName | None
    retryable: bool = False


@dataclass(frozen=True)
class HITLRequest:
    id: uuid.UUID
    prompt: str
    tool_name: str
    tool_args: dict[str, Any] = field(default_factory=dict)


def _merge_errors(
    left: list[AgentErrorRecord], right: list[AgentErrorRecord]
) -> list[AgentErrorRecord]:
    return left + right


def _last_wins(left: Any, right: Any) -> Any:  # noqa: ANN401
    return right if right is not None else left


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: Annotated[AgentName | None, _last_wins]
    plan: Annotated[list[PlanStep], _last_wins]
    artifacts: Annotated[dict[str, Any], _last_wins]
    errors: Annotated[list[AgentErrorRecord], _merge_errors]
    interrupt_request: Annotated[HITLRequest | None, _last_wins]
