"""MCP client registry — pooled sessions, tool cache, allowlist enforcement."""

from __future__ import annotations

import time
from contextlib import AsyncExitStack

from langchain_core.tools import BaseTool
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool as MCPTool

from devhub.adapters.mcp.tool_wrapper import MCPToolWrapper
from devhub.core.errors import ApprovalRequiredError, MCPError, ToolNotAllowedError, with_retries
from devhub.core.logging import get_logger
from devhub.domain.agents import AGENT_CONFIGS
from devhub.domain.models import MCPServerConfig, MCPServerInfo, ToolCall, ToolResult

logger = get_logger(__name__)

_TOOL_CACHE_TTL_S: float = 300.0  # 5-minute TTL on tool schemas


class MCPRegistry:
    """Registry of MCP server connections with per-agent tool allowlists."""

    def __init__(self) -> None:
        self._configs: dict[str, MCPServerConfig] = {}
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stacks: dict[str, AsyncExitStack] = {}
        # tool cache: server_id → (tools, fetched_at)
        self._tool_cache: dict[str, tuple[list[MCPTool], float]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self, config: MCPServerConfig) -> None:
        if config.server_id in self._sessions:
            return  # already connected

        stack = AsyncExitStack()
        try:
            headers: dict[str, str] | None = None
            if config.config and config.config.get("auth_token"):
                headers = {"Authorization": f"Bearer {config.config['auth_token']}"}
            read, write, _ = await stack.enter_async_context(
                streamablehttp_client(config.url, headers=headers)
            )
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
        except Exception as exc:
            await stack.aclose()
            raise MCPError(f"Failed to connect to MCP server '{config.server_id}': {exc}") from exc

        self._configs[config.server_id] = config
        self._sessions[config.server_id] = session
        self._exit_stacks[config.server_id] = stack
        logger.info("mcp.connected", server_id=config.server_id, url=config.url)

    async def disconnect(self, server_id: str) -> None:
        stack = self._exit_stacks.pop(server_id, None)
        self._sessions.pop(server_id, None)
        self._configs.pop(server_id, None)
        self._tool_cache.pop(server_id, None)
        if stack:
            await stack.aclose()
        logger.info("mcp.disconnected", server_id=server_id)

    async def disconnect_all(self) -> None:
        for server_id in list(self._sessions):
            await self.disconnect(server_id)

    # ── Discovery ─────────────────────────────────────────────────────────────

    async def list_servers(self) -> list[MCPServerInfo]:
        result = []
        for server_id, config in self._configs.items():
            cached = self._tool_cache.get(server_id)
            tool_count = len(cached[0]) if cached else 0
            result.append(
                MCPServerInfo(
                    server_id=server_id,
                    url=config.url,
                    connected=server_id in self._sessions,
                    enabled=config.enabled,
                    tool_count=tool_count,
                )
            )
        return result

    async def tools_for(self, agent_id: str) -> list[BaseTool]:
        agent_cfg = AGENT_CONFIGS.get(agent_id)
        if agent_cfg is None:
            raise MCPError(f"Unknown agent_id: {agent_id}")

        tools: list[BaseTool] = []
        for server_id in agent_cfg.allowed_servers:
            if server_id not in self._sessions:
                logger.warning("mcp.server_not_connected", server_id=server_id, agent_id=agent_id)
                continue
            for mcp_tool in await self._get_tools_cached(server_id):
                tools.append(
                    MCPToolWrapper(
                        mcp_tool=mcp_tool,
                        server_id=server_id,
                        agent_id=agent_id,
                        call_fn=self.call,
                    )
                )
        return tools

    async def get_tools_for_server(self, server_id: str) -> list[MCPTool]:
        """Get all tools exposed by a specific server."""
        if server_id not in self._sessions:
            return []
        return await self._get_tools_cached(server_id)

    # ── Tool execution ────────────────────────────────────────────────────────

    async def call(self, tool_call: ToolCall) -> ToolResult:
        server_id = self._resolve_server(tool_call.tool_name, tool_call.agent_id)
        self._enforce_allowlist(tool_call.agent_id, server_id)
        self._enforce_approval(tool_call.tool_name, tool_call.approval_id, server_id)

        session = self._sessions[server_id]
        start = time.monotonic()
        ok = False
        try:
            result = await with_retries(
                lambda: session.call_tool(tool_call.tool_name, tool_call.args),
                max_attempts=3,
                base_delay=0.5,
            )
            ok = not result.isError
            data = _extract_content(result)
            return ToolResult(tool_name=tool_call.tool_name, ok=ok, data=data)
        except MCPError:
            raise
        except Exception as exc:
            raise MCPError(str(exc), cause=exc) from exc
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "mcp.tool_call",
                agent_id=tool_call.agent_id,
                server_id=server_id,
                tool_name=tool_call.tool_name,
                duration_ms=round(duration_ms, 1),
                ok=ok,
            )

    async def is_healthy(self) -> bool:
        if not self._sessions:
            return True  # no servers configured yet — not unhealthy
        return len(self._sessions) > 0

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_tools_cached(self, server_id: str) -> list[MCPTool]:
        cached = self._tool_cache.get(server_id)
        if cached and (time.monotonic() - cached[1]) < _TOOL_CACHE_TTL_S:
            return cached[0]

        session = self._sessions[server_id]
        response = await session.list_tools()
        tools = response.tools
        self._tool_cache[server_id] = (tools, time.monotonic())
        logger.debug("mcp.tools_refreshed", server_id=server_id, count=len(tools))
        return tools

    def _resolve_server(self, tool_name: str, agent_id: str) -> str:
        """Find which connected server owns this tool."""
        for server_id, (tools, _) in self._tool_cache.items():
            if any(t.name == tool_name for t in tools):
                return server_id
        raise MCPError(
            f"Tool '{tool_name}' not found in any connected server",
        )

    def _enforce_allowlist(self, agent_id: str, server_id: str) -> None:
        agent_cfg = AGENT_CONFIGS.get(agent_id)
        if agent_cfg is None or server_id not in agent_cfg.allowed_servers:
            raise ToolNotAllowedError(
                f"Agent '{agent_id}' is not allowed to use tools from server '{server_id}'"
            )

    def _enforce_approval(self, tool_name: str, approval_id: str | None, server_id: str) -> None:
        cached = self._tool_cache.get(server_id)
        if not cached:
            return
        tool = next((t for t in cached[0] if t.name == tool_name), None)
        if tool is None:
            return
        annotations = tool.annotations
        needs_approval = annotations is not None and annotations.readOnlyHint is False
        if needs_approval and approval_id is None:
            raise ApprovalRequiredError(
                f"Tool '{tool_name}' requires human approval (HITL) before execution"
            )


def _extract_content(result: object) -> str:
    """Pull text content from a CallToolResult."""
    content = getattr(result, "content", [])
    parts = []
    for item in content:
        if hasattr(item, "text"):
            parts.append(str(item.text))
        elif hasattr(item, "data"):
            parts.append(str(item.data))
    return "\n".join(parts) if parts else ""
