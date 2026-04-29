"""Port interfaces — abstract contracts that adapters must satisfy.

All protocols use structural subtyping (``typing.Protocol``) so adapters
never import from this module; they just match the shape.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool

from devhub.domain.models import (
    CodeSearchHit,
    MCPServerConfig,
    MCPServerInfo,
    Run,
    Thread,
    ToolCall,
    ToolResult,
    User,
)


@runtime_checkable
class IUserRepository(Protocol):
    async def upsert(self, email: str, name: str | None, avatar_url: str | None) -> User: ...


@runtime_checkable
class IThreadRepository(Protocol):
    async def list_for_user(self, user_id: uuid.UUID) -> list[Thread]: ...

    async def get(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None: ...


@runtime_checkable
class IRunRepository(Protocol):
    async def create(self, thread_id: uuid.UUID) -> Run: ...

    async def get(self, run_id: uuid.UUID) -> Run | None: ...

    async def mark_completed(self, run_id: uuid.UUID) -> None: ...

    async def mark_failed(self, run_id: uuid.UUID, error_data: dict[str, object]) -> None: ...


@runtime_checkable
class IHITLApprovalRepository(Protocol):
    async def create(
        self,
        run_id: uuid.UUID,
        tool_call: dict[str, object],
        summary: str,
        risk: str,
        expires_at: object,
    ) -> object: ...

    async def get(self, approval_id: uuid.UUID) -> object | None: ...

    async def resolve(
        self,
        approval_id: uuid.UUID,
        decision: str,
        patched_args: dict[str, object] | None = None,
    ) -> None: ...

    async def expire_pending(self) -> list[uuid.UUID]: ...


@runtime_checkable
class IAuditLogRepository(Protocol):
    async def log_approval(
        self,
        user_id: uuid.UUID,
        approval_id: uuid.UUID,
        decision: str,
        patched_args: dict[str, object] | None,
    ) -> None: ...


@runtime_checkable
class IMCPRegistry(Protocol):
    async def connect(self, config: MCPServerConfig) -> None: ...

    async def disconnect(self, server_id: str) -> None: ...

    async def list_servers(self) -> list[MCPServerInfo]: ...

    async def tools_for(self, agent_id: str) -> list[BaseTool]: ...

    async def call(self, tool_call: ToolCall) -> ToolResult: ...

    async def is_healthy(self) -> bool: ...


@runtime_checkable
class ILLMClient(Protocol):
    async def is_healthy(self) -> bool: ...


class ILLMPort(Protocol):
    """Thin async chat interface used by domain graph nodes."""

    async def chat(
        self,
        messages: list[BaseMessage],
        *,
        system: str | None = None,
    ) -> AIMessage: ...


@runtime_checkable
class IVectorStore(Protocol):
    """Vector similarity search over embedded code chunks."""

    async def search(self, query: str, *, k: int = 10) -> list[CodeSearchHit]: ...
