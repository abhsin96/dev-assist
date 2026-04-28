from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.cache.redis import get_redis
from devhub.adapters.mcp.registry import MCPRegistry
from devhub.adapters.persistence.database import get_db
from devhub.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "version": "0.1.0", "gitSha": settings.git_sha}


@router.get("/readyz")
async def readyz() -> JSONResponse:
    checks: dict[str, Any] = {}
    ok = True

    # Postgres
    try:
        db_gen = get_db()
        session: AsyncSession = await db_gen.__anext__()
        await session.execute(text("SELECT 1"))
        await db_gen.aclose()
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = str(exc)
        ok = False

    # Redis
    try:
        redis_gen = get_redis()
        redis: Redis = await redis_gen.__anext__()
        await redis.ping()  # type: ignore[misc]
        await redis_gen.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = str(exc)
        ok = False

    # MCP registry
    try:
        registry = MCPRegistry()
        checks["mcp"] = "ok" if await registry.is_healthy() else "degraded"
    except Exception as exc:
        checks["mcp"] = str(exc)
        ok = False

    status_code = 200 if ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )
