from devhub.domain.agents.base import AgentConfig

config = AgentConfig(
    agent_id="supervisor",
    allowed_servers=frozenset(),  # supervisor routes only; no direct tool access
)
