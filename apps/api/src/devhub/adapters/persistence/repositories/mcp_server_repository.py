"""Repository implementation for MCP server persistence."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.models.mcp_servers import MCPServer as OrmMCPServer
from devhub.domain.models import MCPServerCreate, MCPServerInfo, MCPServerUpdate


class MCPServerRepository:
    """Persistence adapter for MCP server configurations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[MCPServerInfo]:
        """List all MCP servers."""
        result = await self._session.execute(select(OrmMCPServer))
        servers = result.scalars().all()
        return [self._to_domain(server) for server in servers]

    async def get(self, server_id: str) -> MCPServerInfo | None:
        """Get a specific MCP server by server_id."""
        result = await self._session.execute(
            select(OrmMCPServer).where(OrmMCPServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()
        return self._to_domain(server) if server else None

    async def create(self, server: MCPServerCreate) -> MCPServerInfo:
        """Create a new MCP server configuration."""
        orm_server = OrmMCPServer(
            id=uuid.uuid4(),
            server_id=server.server_id,
            url=server.url,
            transport=server.transport,
            enabled=True,
            config=server.config,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._session.add(orm_server)
        await self._session.flush()
        return self._to_domain(orm_server)

    async def update(self, server_id: str, updates: MCPServerUpdate) -> MCPServerInfo | None:
        """Update an existing MCP server configuration."""
        result = await self._session.execute(
            select(OrmMCPServer).where(OrmMCPServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()
        if not server:
            return None

        if updates.url is not None:
            server.url = updates.url
        if updates.enabled is not None:
            server.enabled = updates.enabled
        if updates.config is not None:
            server.config = updates.config

        server.updated_at = datetime.utcnow()
        await self._session.flush()
        return self._to_domain(server)

    async def delete(self, server_id: str) -> None:
        """Delete an MCP server configuration."""
        result = await self._session.execute(
            select(OrmMCPServer).where(OrmMCPServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()
        if server:
            await self._session.delete(server)
            await self._session.flush()

    async def update_connection_status(
        self,
        server_id: str,
        connected: bool,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update the connection status and error information for a server."""
        result = await self._session.execute(
            select(OrmMCPServer).where(OrmMCPServer.server_id == server_id)
        )
        server = result.scalar_one_or_none()
        if server:
            if connected:
                server.last_connected_at = datetime.utcnow()
                server.error_code = None
                server.error_message = None
            else:
                server.error_code = error_code
                server.error_message = error_message
            server.updated_at = datetime.utcnow()
            await self._session.flush()

    def _to_domain(self, orm_server: OrmMCPServer) -> MCPServerInfo:
        """Convert ORM model to domain model."""
        return MCPServerInfo(
            server_id=orm_server.server_id,
            url=orm_server.url,
            connected=orm_server.last_connected_at is not None,
            enabled=orm_server.enabled,
            tool_count=0,  # Will be populated by registry
            tools=[],  # Will be populated by registry
            error_code=orm_server.error_code,
            error_message=orm_server.error_message,
            last_connected_at=orm_server.last_connected_at,
        )
