# [DEVHUB-024] MCP connections page (list, add, disable)

**Labels:** `epic:mcp-management` `area:web` `type:feature` `priority:P1`
**Estimate:** 3 pts
**Depends on:** DEVHUB-009, DEVHUB-016

## Story
**As a** user,
**I want** a settings page to see, add, and disable MCP connections,
**so that** I control what tools agents can use on my behalf.

## Acceptance criteria
- [ ] `/settings/connections` lists all available MCP servers with status (connected, error, disabled).
- [ ] Each row shows the tools the server exposes (cached from `list_tools`).
- [ ] Per-server toggle to disable; disabled servers are removed from agent allowlists at runtime.
- [ ] "Add connection" opens a typed form for the server's required config (URL, env, OAuth trigger).
- [ ] On error states, the row shows the typed error code and a "Reconnect" action.

## Definition of done
- Demo: disable the GitHub server, run a PR review request, observe the agent gracefully reporting the missing capability.
