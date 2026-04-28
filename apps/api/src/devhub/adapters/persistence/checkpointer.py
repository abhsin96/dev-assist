"""Factory for the LangGraph Postgres checkpointer.

Uses psycopg (v3) directly — the connection string must use the plain
``postgresql://`` scheme, not the SQLAlchemy ``postgresql+asyncpg://`` form.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from devhub.core.settings import get_settings


def _pg_dsn() -> str:
    """Convert SQLAlchemy asyncpg URL → plain psycopg URL."""
    url = get_settings().database_url
    return url.replace("postgresql+asyncpg://", "postgresql://")


@asynccontextmanager
async def make_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """Async context manager that yields a ready-to-use checkpointer."""
    async with AsyncPostgresSaver.from_conn_string(_pg_dsn()) as saver:
        await saver.setup()
        yield saver
