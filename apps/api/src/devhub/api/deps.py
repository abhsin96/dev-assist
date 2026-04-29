from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.auth.jwt import decode_api_token
from devhub.adapters.cache.redis import get_redis
from devhub.adapters.llm.client import AnthropicLLMClient
from devhub.adapters.mcp.registry import MCPRegistry
from devhub.adapters.persistence.database import get_db
from devhub.adapters.persistence.repositories import (
    AuditLogRepository,
    HITLApprovalRepository,
    RunRepository,
    ThreadRepository,
    UserRepository,
)
from devhub.adapters.streaming.event_store import EventStore
from devhub.application.use_cases.create_thread import CreateThreadUseCase
from devhub.application.use_cases.delete_thread import DeleteThreadUseCase
from devhub.application.use_cases.get_thread import GetThreadUseCase
from devhub.application.use_cases.list_threads import ListThreadsUseCase
from devhub.application.use_cases.update_thread import UpdateThreadUseCase
from devhub.core.errors import AuthError
from devhub.core.settings import get_settings
from devhub.domain.ports import (
    IAuditLogRepository,
    IHITLApprovalRepository,
    ILLMClient,
    IMCPRegistry,
    IRunRepository,
    IThreadRepository,
    IUserRepository,
)

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> dict[str, object]:
    if not credentials:
        raise AuthError("Authentication required")
    return decode_api_token(credentials.credentials)


CurrentUser = Annotated[dict[str, object], Security(get_current_user)]


async def get_current_user_id(
    claims: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> uuid.UUID:
    """Resolve the caller's DB user UUID from JWT claims.

    The BFF mints tokens with sub=email. This dep upserts the user row on first
    call so every authenticated endpoint gets a stable UUID without any extra
    round-trip from the web layer.
    """
    email = str(claims["sub"])
    name = str(claims["name"]) if claims.get("name") else None
    image = str(claims["image"]) if claims.get("image") else None
    user = await UserRepository(session).upsert(email, name, image)
    return user.id


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]


# ── Persistence repos ─────────────────────────────────────────────────────────


def get_user_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IUserRepository:
    return UserRepository(session)


def get_thread_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IThreadRepository:
    return ThreadRepository(session)


def get_run_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IRunRepository:
    return RunRepository(session)


def get_hitl_approval_repo(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IHITLApprovalRepository:
    return HITLApprovalRepository(session)


def get_audit_log_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IAuditLogRepository:
    return AuditLogRepository(session)


# ── Infrastructure clients ────────────────────────────────────────────────────


def get_mcp_registry() -> IMCPRegistry:
    return MCPRegistry()


def get_llm_client() -> ILLMClient:
    settings = get_settings()
    return AnthropicLLMClient(api_key=settings.anthropic_api_key)


# ── App-state singletons (graph + event store) ────────────────────────────────


def get_graph(request: Request) -> Any:
    return request.app.state.graph


def get_event_store(request: Request) -> EventStore:
    return request.app.state.event_store  # type: ignore[no-any-return]


# ── Use-case factories ────────────────────────────────────────────────────────


def get_list_threads_use_case(
    repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
) -> ListThreadsUseCase:
    return ListThreadsUseCase(repo)


def get_create_thread_use_case(
    repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
) -> CreateThreadUseCase:
    return CreateThreadUseCase(repo)


def get_get_thread_use_case(
    repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
) -> GetThreadUseCase:
    return GetThreadUseCase(repo)


def get_update_thread_use_case(
    repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
) -> UpdateThreadUseCase:
    return UpdateThreadUseCase(repo)


def get_delete_thread_use_case(
    repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
) -> DeleteThreadUseCase:
    return DeleteThreadUseCase(repo)


# ── Re-export redis for health checks ─────────────────────────────────────────
__all__ = [
    "CurrentUser",
    "get_audit_log_repo",
    "get_create_thread_use_case",
    "get_current_user",
    "get_db",
    "get_delete_thread_use_case",
    "get_event_store",
    "get_get_thread_use_case",
    "get_graph",
    "get_hitl_approval_repo",
    "get_llm_client",
    "get_list_threads_use_case",
    "get_mcp_registry",
    "get_redis",
    "get_run_repo",
    "get_thread_repo",
    "get_update_thread_use_case",
    "get_user_repo",
]
