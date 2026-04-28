"""Typed events yielded by StartRun / ResumeRun.

Matches ARCHITECTURE.md §7 event types exactly. SSE encoding lives in the
streaming adapter so the application layer stays transport-agnostic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class TokenEvent:
    text: str
    type: Literal["token"] = field(default="token", init=False)


@dataclass(frozen=True)
class ToolCallEvent:
    id: str
    name: str
    args: dict[str, Any]
    type: Literal["tool_call"] = field(default="tool_call", init=False)


@dataclass(frozen=True)
class ToolResultEvent:
    id: str
    ok: bool
    data: Any = None
    error: str | None = None
    type: Literal["tool_result"] = field(default="tool_result", init=False)


@dataclass(frozen=True)
class StateEvent:
    current_agent: str | None
    plan: list[Any]
    type: Literal["state"] = field(default="state", init=False)


@dataclass(frozen=True)
class InterruptEvent:
    request_id: str
    prompt: str
    tool_name: str
    type: Literal["interrupt"] = field(default="interrupt", init=False)


@dataclass(frozen=True)
class ErrorEvent:
    code: str
    message: str
    retryable: bool = False
    type: Literal["error"] = field(default="error", init=False)


@dataclass(frozen=True)
class DoneEvent:
    run_id: uuid.UUID
    final_message: str
    type: Literal["done"] = field(default="done", init=False)


RunEvent = (
    TokenEvent
    | ToolCallEvent
    | ToolResultEvent
    | StateEvent
    | InterruptEvent
    | ErrorEvent
    | DoneEvent
)
