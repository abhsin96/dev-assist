from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.auth.jwt import decode_api_token
from devhub.adapters.cache.redis import get_redis
from devhub.adapters.llm.client import AnthropicLLMClient
from devhub.adapters.mcp.registry import MCPRegistry
from devhub.adapters.persistence.database import get_db
from devhub.adapters.persistence.repositories import RunRepository, ThreadRepository, UserRepository
from devhub.adapters.streaming.event_store import EventStore
from devhub.application.use_cases.list_threads import ListThreadsUseCase
from devhub.core.errors import AuthError
from devhub.core.settings import get_settings
from devhub.domain.ports import (
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


# ── Persistence repos ─────────────────────────────────────────────────────────


def get_user_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IUserRepository:
    return UserRepository(session)


def get_thread_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IThreadRepository:
    return ThreadRepository(session)


def get_run_repo(session: Annotated[AsyncSession, Depends(get_db)]) -> IRunRepository:
    return RunRepository(session)


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


# ── Re-export redis for health checks ─────────────────────────────────────────
__all__ = [
    "CurrentUser",
    "get_current_user",
    "get_db",
    "get_event_store",
    "get_graph",
    "get_llm_client",
    "get_list_threads_use_case",
    "get_mcp_registry",
    "get_redis",
    "get_run_repo",
    "get_thread_repo",
    "get_user_repo",
]
