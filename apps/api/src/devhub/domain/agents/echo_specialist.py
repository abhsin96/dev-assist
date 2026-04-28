from devhub.domain.agents.base import AgentConfig

config = AgentConfig(
    agent_id="echo_specialist",
    allowed_servers=frozenset(),  # placeholder; real specialists added in DEVHUB-011+
)
