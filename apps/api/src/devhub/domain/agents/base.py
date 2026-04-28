"""Base type for per-agent configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentConfig:
    """Static configuration for one agent.

    ``allowed_servers`` is the set of MCP server IDs this agent may access.
    An empty set means the agent uses no MCP tools (e.g. the supervisor).
    """

    agent_id: str
    allowed_servers: frozenset[str] = field(default_factory=frozenset)
