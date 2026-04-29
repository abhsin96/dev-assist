"""API router for MCP server connection management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.mcp.registry import MCPRegistry
from devhub.adapters.persistence.database import get_db
from devhub.adapters.persistence.repositories.mcp_server_repository import MCPServerRepository
from devhub.core.logging import get_logger
from devhub.domain.models import MCPServerConfig, MCPServerCreate, MCPServerInfo, MCPServerUpdate

logger = get_logger(__name__)

router = APIRouter(tags=["mcp-connections"])


def get_mcp_registry() -> MCPRegistry:
    """Dependency to get the MCP registry from app state."""
    from devhub.main import app

    return app.state.mcp_registry  # type: ignore[no-any-return]


@router.get("/mcp/servers", response_model=list[MCPServerInfo])
async def list_mcp_servers(
    session: Annotated[AsyncSession, Depends(get_db)],
    registry: Annotated[MCPRegistry, Depends(get_mcp_registry)],
) -> list[MCPServerInfo]:
    """List all MCP servers with their connection status and tools."""
    repo = MCPServerRepository(session)
    servers = await repo.list_all()

    # Enrich with runtime information from registry
    registry_servers = await registry.list_servers()
    registry_map = {s.server_id: s for s in registry_servers}

    enriched = []
    for server in servers:
        runtime_info = registry_map.get(server.server_id)
        if runtime_info:
            # Get tools from registry
            tools = await registry.get_tools_for_server(server.server_id)
            enriched.append(
                MCPServerInfo(
                    server_id=server.server_id,
                    url=server.url,
                    connected=runtime_info.connected,
                    enabled=server.enabled,
                    tool_count=len(tools),
                    tools=[t.name for t in tools],
                    error_code=server.error_code,
                    error_message=server.error_message,
                    last_connected_at=server.last_connected_at,
                )
            )
        else:
            enriched.append(server)

    return enriched


@router.post("/mcp/servers", response_model=MCPServerInfo, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server: MCPServerCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    registry: Annotated[MCPRegistry, Depends(get_mcp_registry)],
) -> MCPServerInfo:
    """Add a new MCP server connection."""
    repo = MCPServerRepository(session)

    # Check if server already exists
    existing = await repo.get(server.server_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MCP server '{server.server_id}' already exists",
        )

    # Create in database
    created = await repo.create(server)
    await session.commit()

    # Connect to the server
    try:
        config = MCPServerConfig(
            server_id=server.server_id,
            url=server.url,
            transport=server.transport,
            enabled=True,
            config=server.config,
        )
        await registry.connect(config)
        await repo.update_connection_status(server.server_id, connected=True)
        await session.commit()
    except Exception as exc:
        logger.error(
            "mcp.connection_failed",
            server_id=server.server_id,
            error=str(exc),
        )
        await repo.update_connection_status(
            server.server_id,
            connected=False,
            error_code="CONNECTION_FAILED",
            error_message=str(exc),
        )
        await session.commit()

    return await repo.get(server.server_id) or created


@router.patch("/mcp/servers/{server_id}", response_model=MCPServerInfo)
async def update_mcp_server(
    server_id: str,
    updates: MCPServerUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    registry: Annotated[MCPRegistry, Depends(get_mcp_registry)],
) -> MCPServerInfo:
    """Update an MCP server configuration."""
    repo = MCPServerRepository(session)

    # Check if server exists
    existing = await repo.get(server_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_id}' not found",
        )

    # Update in database
    updated = await repo.update(server_id, updates)
    await session.commit()

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_id}' not found",
        )

    # If enabled status changed, connect or disconnect
    if updates.enabled is not None:
        if updates.enabled:
            try:
                config = MCPServerConfig(
                    server_id=server_id,
                    url=updated.url,
                    transport="streamable-http",
                    enabled=True,
                )
                await registry.connect(config)
                await repo.update_connection_status(server_id, connected=True)
                await session.commit()
            except Exception as exc:
                logger.error(
                    "mcp.connection_failed",
                    server_id=server_id,
                    error=str(exc),
                )
                await repo.update_connection_status(
                    server_id,
                    connected=False,
                    error_code="CONNECTION_FAILED",
                    error_message=str(exc),
                )
                await session.commit()
        else:
            await registry.disconnect(server_id)
            await repo.update_connection_status(server_id, connected=False)
            await session.commit()

    return await repo.get(server_id) or updated


@router.delete("/mcp/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    registry: Annotated[MCPRegistry, Depends(get_mcp_registry)],
) -> None:
    """Delete an MCP server connection."""
    repo = MCPServerRepository(session)

    # Check if server exists
    existing = await repo.get(server_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_id}' not found",
        )

    # Disconnect from registry
    await registry.disconnect(server_id)

    # Delete from database
    await repo.delete(server_id)
    await session.commit()


@router.post("/mcp/servers/{server_id}/reconnect", response_model=MCPServerInfo)
async def reconnect_mcp_server(
    server_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    registry: Annotated[MCPRegistry, Depends(get_mcp_registry)],
) -> MCPServerInfo:
    """Attempt to reconnect to an MCP server."""
    repo = MCPServerRepository(session)

    # Check if server exists
    existing = await repo.get(server_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_id}' not found",
        )

    # Disconnect first if connected
    await registry.disconnect(server_id)

    # Attempt to reconnect
    try:
        config = MCPServerConfig(
            server_id=server_id,
            url=existing.url,
            transport="streamable-http",
            enabled=existing.enabled,
        )
        await registry.connect(config)
        await repo.update_connection_status(server_id, connected=True)
        await session.commit()
        logger.info("mcp.reconnected", server_id=server_id)
    except Exception as exc:
        logger.error(
            "mcp.reconnection_failed",
            server_id=server_id,
            error=str(exc),
        )
        await repo.update_connection_status(
            server_id,
            connected=False,
            error_code="CONNECTION_FAILED",
            error_message=str(exc),
        )
        await session.commit()

    updated = await repo.get(server_id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_id}' not found",
        )

    return updated
