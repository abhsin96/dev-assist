"""Agent configuration registry.

Maps agent_id → AgentConfig. Add new agent modules here as they are implemented.
"""

from __future__ import annotations

from devhub.domain.agents import echo_specialist, pr_reviewer, supervisor
from devhub.domain.agents.base import AgentConfig

AGENT_CONFIGS: dict[str, AgentConfig] = {
    supervisor.config.agent_id: supervisor.config,
    echo_specialist.config.agent_id: echo_specialist.config,
    pr_reviewer.config.agent_id: pr_reviewer.config,
}

__all__ = ["AGENT_CONFIGS", "AgentConfig"]
