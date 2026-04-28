# [DEVHUB-009] MCP client registry + per-agent tool allowlists

**Labels:** `epic:backend-runtime` `area:mcp` `type:feature` `priority:P0`
**Estimate:** 5 pts
**Depends on:** DEVHUB-008

## Story
**As an** agent developer,
**I want** a single registry that connects to MCP servers and exposes their tools as LangChain tools — gated by per-agent allowlists,
**so that** adding a connector is a config change and least-privilege is enforced server-side.

## Acceptance criteria
- [ ] `adapters/mcp/registry.py` implements `MCPRegistry` with: `connect`, `disconnect`, `list_servers`, `tools_for(agent_id)`, `call(tool_call)`.
- [ ] Connections are pooled and reused across requests; disconnections are graceful on shutdown.
- [ ] Each MCP `Tool` is wrapped as a LangChain `BaseTool` with: typed args via Pydantic, MCP server metadata, `requires_approval` flag.
- [ ] Per-agent allowlists are defined in `domain/agents/<agent>.py` (e.g. `pr_reviewer.allowed_servers = ["github"]`).
- [ ] Calls to non-allowlisted tools raise `MCPError(code="TOOL_NOT_ALLOWED")` and never reach the network.
- [ ] All tool calls are logged with `agent_id`, `server_id`, `tool_name`, `duration_ms`, `ok`.
- [ ] Retries are applied per `with_retries(...)` for `retriable=True` MCP errors (timeouts, 5xx).
- [ ] `requires_approval=True` tools refuse to execute without an `approval_id` matching a recorded HITL approval (DEVHUB-015).

## Technical notes
- Use the official MCP Python SDK transport (stdio or streamable-http).
- Cache tool schemas per server with TTL; refresh on `tools/list_changed` notifications.

## Definition of done
- An integration test connects to the dockerized GitHub MCP server, calls `repos.search`, asserts a typed result, and verifies a denied tool raises `TOOL_NOT_ALLOWED`.
