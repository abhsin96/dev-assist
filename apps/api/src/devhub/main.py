"""Application entry point.

Boot order:
1. Load settings (reads .env)
2. Push LangSmith env vars so langchain picks them up at import time
3. Configure structlog
4. Init Sentry
5. Build FastAPI app and attach middleware
"""

from __future__ import annotations

import os

# ── 1. Settings ───────────────────────────────────────────────────────────────
from devhub.core.settings import get_settings

settings = get_settings()

# ── 2. LangSmith – must be set before any langchain import ───────────────────
if settings.langchain_tracing_v2:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

# ── 3. Structured logging ─────────────────────────────────────────────────────
from devhub.core.logging import configure_logging, get_logger  # noqa: E402

configure_logging(
    log_level=settings.log_level,
    json_logs=settings.app_env != "development",
)

logger = get_logger(__name__)

# ── 4. Sentry ─────────────────────────────────────────────────────────────────
if settings.sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=settings.git_sha,
        environment=settings.app_env,
        traces_sample_rate=0.2,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        # Never send secrets
        send_default_pii=False,
    )
    logger.info("sentry.initialized", release=settings.git_sha)

# ── 5. FastAPI app ────────────────────────────────────────────────────────────
from collections.abc import AsyncIterator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from langgraph.checkpoint.memory import MemorySaver  # noqa: E402

from devhub.adapters.streaming.event_store import EventStore  # noqa: E402
from devhub.api.deps import get_llm_client  # noqa: E402
from devhub.api.error_handlers import register_error_handlers  # noqa: E402
from devhub.api.middleware import RequestIdMiddleware  # noqa: E402
from devhub.api.routers.auth import router as auth_router  # noqa: E402
from devhub.api.routers.health import router as health_router  # noqa: E402
from devhub.api.routers.mcp_connections import router as mcp_router  # noqa: E402
from devhub.api.routers.oauth_connect import router as oauth_router  # noqa: E402
from devhub.api.routers.runs import router as runs_router  # noqa: E402
from devhub.api.routers.threads import router as threads_router  # noqa: E402
from devhub.domain.graphs.supervisor import compile_supervisor_graph  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from devhub.adapters.mcp.registry import MCPRegistry
    from devhub.adapters.persistence.database import get_session_factory
    from devhub.adapters.persistence.repositories import HITLApprovalRepository
    from devhub.adapters.persistence.repositories.mcp_server_repository import (
        MCPServerRepository,
    )
    from devhub.application.use_cases.expire_approvals import ExpireApprovalsTask
    from devhub.domain.models import MCPServerConfig

    llm = get_llm_client()
    app.state.graph = compile_supervisor_graph(llm, MemorySaver())
    app.state.event_store = EventStore()

    # Initialize MCP registry
    mcp_registry = MCPRegistry()
    app.state.mcp_registry = mcp_registry

    # Load and connect to enabled MCP servers from database
    async with get_session_factory()() as session:
        mcp_repo = MCPServerRepository(session)
        servers = await mcp_repo.list_all()
        for server in servers:
            if server.enabled:
                try:
                    extra_config = dict(server.config or {})
                    if server.server_id == "github" and settings.github_token:
                        extra_config.setdefault("auth_token", settings.github_token)
                    config = MCPServerConfig(
                        server_id=server.server_id,
                        url=server.url,
                        transport="streamable-http",
                        enabled=True,
                        config=extra_config or None,
                    )
                    await mcp_registry.connect(config)
                    await mcp_repo.update_connection_status(server.server_id, connected=True)
                    logger.info("mcp.server_connected_on_startup", server_id=server.server_id)
                except Exception as exc:
                    logger.error(
                        "mcp.server_connection_failed_on_startup",
                        server_id=server.server_id,
                        error=str(exc),
                    )
                    await mcp_repo.update_connection_status(
                        server.server_id,
                        connected=False,
                        error_code="CONNECTION_FAILED",
                        error_message=str(exc),
                    )
        await session.commit()

    logger.info("app.graph_ready")

    # Create a session for the background task that will live for the app lifetime
    # Note: This session is managed manually and closed in the shutdown phase
    background_session = get_session_factory()()
    app.state.background_session = background_session

    # Start background task to expire approvals
    approval_repo = HITLApprovalRepository(background_session)
    expire_task = ExpireApprovalsTask(approval_repo, interval_seconds=60)
    await expire_task.start()
    app.state.expire_task = expire_task
    logger.info("app.expire_approvals_task_started")

    yield

    # Disconnect all MCP servers
    if hasattr(app.state, "mcp_registry"):
        await app.state.mcp_registry.disconnect_all()
        logger.info("app.mcp_servers_disconnected")

    # Stop background task
    if hasattr(app.state, "expire_task"):
        await app.state.expire_task.stop()
        logger.info("app.expire_approvals_task_stopped")

    # Close the background session using async context manager protocol
    if hasattr(app.state, "background_session"):
        await app.state.background_session.close()
        logger.info("app.background_session_closed")

    logger.info("app.shutting_down")


app = FastAPI(
    title="DevHub AI API",
    version="0.1.0",
    openapi_url="/openapi.json" if settings.app_env != "prod" else None,
    lifespan=lifespan,
)

# CORS middleware - allow frontend to access API from different port
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",  # Alternative dev port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers including X-Request-Id
)

app.add_middleware(RequestIdMiddleware)
register_error_handlers(app)

app.include_router(auth_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(mcp_router, prefix="/api")
app.include_router(oauth_router, prefix="/api")
app.include_router(threads_router, prefix="/api")
app.include_router(runs_router, prefix="/api")

logger.info(
    "app.started",
    env=settings.app_env,
    langsmith_tracing=settings.langchain_tracing_v2,
    sentry_enabled=bool(settings.sentry_dsn),
)
