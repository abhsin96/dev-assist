"""Tests for MCPRegistry — allowlist enforcement, tool wrapping, logging, retries.

All tests mock the MCP ClientSession; no real MCP server required.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from mcp.types import CallToolResult, ListToolsResult, TextContent, ToolAnnotations
from mcp.types import Tool as MCPTool

from devhub.adapters.mcp.registry import MCPRegistry
from devhub.adapters.mcp.tool_wrapper import MCPToolWrapper
from devhub.core.errors import ApprovalRequiredError, ToolNotAllowedError
from devhub.domain.agents import AGENT_CONFIGS
from devhub.domain.agents.base import AgentConfig
from devhub.domain.models import MCPServerConfig, ToolCall

# ── Fixtures ──────────────────────────────────────────────────────────────────

_GITHUB_TOOL = MCPTool(
    name="search_repos",
    description="Search GitHub repositories",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results"},
        },
        "required": ["query"],
    },
)

_WRITE_TOOL = MCPTool(
    name="create_issue",
    description="Create a GitHub issue",
    inputSchema={"type": "object", "properties": {}},
    annotations=ToolAnnotations(readOnlyHint=False),
)

_SERVER_CFG = MCPServerConfig(server_id="github", url="http://localhost:3001")


def _make_mock_session(tools: list[MCPTool], call_result: str = "ok") -> AsyncMock:
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=ListToolsResult(tools=tools))
    session.call_tool = AsyncMock(
        return_value=CallToolResult(
            content=[TextContent(type="text", text=call_result)],
            isError=False,
        )
    )
    return session


def _make_registry_with_session(
    session: AsyncMock,
    tools: list[MCPTool],
    server_id: str = "github",
) -> MCPRegistry:
    """Build a registry that already 'has' a connected session (bypasses real connect)."""
    r = MCPRegistry()
    r._configs[server_id] = _SERVER_CFG
    r._sessions[server_id] = session
    r._tool_cache[server_id] = (tools, time.monotonic())
    return r


# ── Agent config helpers ──────────────────────────────────────────────────────


def _with_agent(agent_id: str, allowed_servers: frozenset[str]):
    """Temporarily add an agent config for a test."""
    cfg = AgentConfig(agent_id=agent_id, allowed_servers=allowed_servers)
    AGENT_CONFIGS[agent_id] = cfg
    return cfg


# ── Tests: tool_wrapper ───────────────────────────────────────────────────────


def test_tool_wrapper_name_and_description() -> None:
    call_fn = AsyncMock(return_value=MagicMock(ok=True, data="result"))
    wrapper = MCPToolWrapper(
        mcp_tool=_GITHUB_TOOL,
        server_id="github",
        agent_id="pr_reviewer",
        call_fn=call_fn,
    )
    assert wrapper.name == "search_repos"
    assert "GitHub" in wrapper.description


def test_tool_wrapper_requires_approval_from_annotation() -> None:
    call_fn = AsyncMock()
    wrapper = MCPToolWrapper(
        mcp_tool=_WRITE_TOOL,
        server_id="github",
        agent_id="pr_reviewer",
        call_fn=call_fn,
    )
    assert wrapper.requires_approval is True


def test_tool_wrapper_args_schema_has_required_field() -> None:
    call_fn = AsyncMock()
    wrapper = MCPToolWrapper(
        mcp_tool=_GITHUB_TOOL,
        server_id="github",
        agent_id="pr_reviewer",
        call_fn=call_fn,
    )
    schema = wrapper.args_schema.model_json_schema()
    assert "query" in schema["properties"]
    assert "query" in schema.get("required", [])


@pytest.mark.asyncio
async def test_tool_wrapper_arun_invokes_call_fn() -> None:
    from devhub.domain.models import ToolResult

    call_fn = AsyncMock(return_value=ToolResult(tool_name="search_repos", ok=True, data="repos"))
    wrapper = MCPToolWrapper(
        mcp_tool=_GITHUB_TOOL,
        server_id="github",
        agent_id="pr_reviewer",
        call_fn=call_fn,
    )
    result = await wrapper._arun(query="devhub")
    assert result == "repos"
    call_fn.assert_awaited_once()


# ── Tests: allowlist enforcement ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_raises_tool_not_allowed_for_unauthorized_agent() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    # pr_reviewer_test not allowed to use github
    _with_agent("pr_reviewer_test", frozenset())  # empty allowed_servers
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    with pytest.raises(ToolNotAllowedError):
        await registry.call(
            ToolCall(tool_name="search_repos", args={"query": "x"}, agent_id="pr_reviewer_test")
        )


@pytest.mark.asyncio
async def test_call_succeeds_for_authorized_agent() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    _with_agent("pr_reviewer_allowed", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    result = await registry.call(
        ToolCall(tool_name="search_repos", args={"query": "x"}, agent_id="pr_reviewer_allowed")
    )
    assert result.ok is True


# ── Tests: approval enforcement ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_raises_approval_required_for_write_tool_without_id() -> None:
    session = _make_mock_session([_WRITE_TOOL])
    _with_agent("issue_triager_test", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_WRITE_TOOL])

    with pytest.raises(ApprovalRequiredError):
        await registry.call(
            ToolCall(
                tool_name="create_issue",
                args={},
                agent_id="issue_triager_test",
                approval_id=None,
            )
        )


@pytest.mark.asyncio
async def test_call_proceeds_for_write_tool_with_approval_id() -> None:
    session = _make_mock_session([_WRITE_TOOL])
    _with_agent("issue_triager_approved", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_WRITE_TOOL])

    result = await registry.call(
        ToolCall(
            tool_name="create_issue",
            args={},
            agent_id="issue_triager_approved",
            approval_id="hitl-approval-123",
        )
    )
    assert result.ok is True


# ── Tests: tool cache ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tools_for_returns_tools_for_allowed_servers() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    _with_agent("searcher_test", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    tools = await registry.tools_for("searcher_test")
    assert len(tools) == 1
    assert tools[0].name == "search_repos"


@pytest.mark.asyncio
async def test_tools_for_returns_empty_for_no_allowed_servers() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    # supervisor has no allowed servers
    tools = await registry.tools_for("supervisor")
    assert tools == []


@pytest.mark.asyncio
async def test_tool_cache_ttl_refresh() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    _with_agent("cache_agent", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    # Expire the cache
    registry._tool_cache["github"] = ([_GITHUB_TOOL], time.monotonic() - 9999)
    await registry.tools_for("cache_agent")

    # list_tools should have been called to refresh
    session.list_tools.assert_awaited_once()


# ── Tests: logging ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_logs_tool_invocation() -> None:
    from unittest.mock import patch

    session = _make_mock_session([_GITHUB_TOOL])
    _with_agent("log_agent", frozenset({"github"}))
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    with patch("devhub.adapters.mcp.registry.logger") as mock_log:
        await registry.call(
            ToolCall(tool_name="search_repos", args={"query": "x"}, agent_id="log_agent")
        )

    mock_log.info.assert_called_with(
        "mcp.tool_call",
        agent_id="log_agent",
        server_id="github",
        tool_name="search_repos",
        duration_ms=mock_log.info.call_args.kwargs["duration_ms"],
        ok=True,
    )


# ── Tests: list_servers ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_servers_shows_connected_server() -> None:
    session = _make_mock_session([_GITHUB_TOOL])
    registry = _make_registry_with_session(session, [_GITHUB_TOOL])

    servers = await registry.list_servers()
    assert len(servers) == 1
    assert servers[0].server_id == "github"
    assert servers[0].connected is True
    assert servers[0].tool_count == 1
