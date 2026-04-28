"""Typed events yielded by StartRun / ResumeRun.

Matches ARCHITECTURE.md §7 event types; SSE encoding is in the streaming adapter.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class TokenEvent:
    text: str
    type: Literal["token"] = field(default="token", init=False)


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


RunEvent = TokenEvent | ErrorEvent | DoneEvent
