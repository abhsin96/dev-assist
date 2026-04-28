"""Wraps an MCP Tool as a LangChain BaseTool with a typed Pydantic args schema."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.tools import BaseTool
from mcp.types import Tool as MCPTool
from pydantic import BaseModel, Field, create_model

from devhub.domain.models import ToolCall, ToolResult

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "object": dict,
    "array": list,
}


def _build_args_schema(mcp_tool: MCPTool) -> type[BaseModel]:
    """Dynamically create a Pydantic model from the tool's JSON Schema."""
    schema = mcp_tool.inputSchema or {}
    properties: dict[str, Any] = schema.get("properties", {})
    required: set[str] = set(schema.get("required", []))

    fields: dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        py_type = _JSON_TYPE_MAP.get(prop_def.get("type", "string"), str)
        description = prop_def.get("description", "")
        if prop_name in required:
            fields[prop_name] = (py_type, Field(..., description=description))
        else:
            fields[prop_name] = (py_type | None, Field(default=None, description=description))

    model_name = "".join(p.title() for p in mcp_tool.name.replace("-", "_").split("_")) + "Args"
    return create_model(model_name, **fields)


class MCPToolWrapper(BaseTool):
    """LangChain-compatible tool backed by an MCP server call."""

    name: str
    description: str
    server_id: str
    agent_id: str
    requires_approval: bool
    _call_fn: Callable[[ToolCall], Awaitable[ToolResult]]

    def __init__(
        self,
        mcp_tool: MCPTool,
        server_id: str,
        agent_id: str,
        call_fn: Callable[[ToolCall], Awaitable[ToolResult]],
        *,
        requires_approval: bool = False,
    ) -> None:
        annotations = mcp_tool.annotations
        inferred_approval = requires_approval or (
            annotations is not None and annotations.readOnlyHint is False
        )
        super().__init__(
            name=mcp_tool.name,
            description=mcp_tool.description or mcp_tool.name,
            args_schema=_build_args_schema(mcp_tool),
            server_id=server_id,
            agent_id=agent_id,
            requires_approval=inferred_approval,
        )
        object.__setattr__(self, "_call_fn", call_fn)

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("Use async _arun; MCP calls are async-only")

    async def _arun(self, **kwargs: Any) -> str:
        result = await self._call_fn(
            ToolCall(
                tool_name=self.name,
                args=kwargs,
                agent_id=self.agent_id,
            )
        )
        if not result.ok:
            raise RuntimeError(result.error or "MCP tool call failed")
        return str(result.data)
