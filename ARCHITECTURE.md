# DevHub AI — Architecture

## 1. Goals & non-goals

**Goals**
- Multi-agent orchestration with a supervisor + specialist topology.
- MCP as the single tool/data plane — agents do not talk to vendor SDKs directly.
- Streaming-first UX: tokens, tool calls, and intermediate steps stream to the UI in real time.
- Durable runs: any conversation can be paused, inspected, and resumed (incl. human-in-the-loop approvals).
- Generic, layered error handling that surfaces actionable messages to both the agent (for self-correction) and the user (for recovery).

**Non-goals (v1)**
- Multi-tenant SaaS billing.
- Custom model fine-tuning.
- Mobile-native apps.

## 2. High-level topology

```
┌────────────────────────────────────────────────────────────────────┐
│                           Next.js Web App                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐    │
│  │ Thread UI    │  │ Trace Viewer │  │ MCP Connection Manager │    │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────────┘    │
│         │ SSE/WS          │ REST              │ REST               │
└─────────┼─────────────────┼───────────────────┼───────────────────┘
          ▼                 ▼                   ▼
┌────────────────────────────────────────────────────────────────────┐
│                       FastAPI (apps/api)                           │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │ Routers  │→ │ Application    │→ │ Domain       │→ │ Adapters │  │
│  │ (HTTP)   │  │ Services       │  │ (Agents/     │  │ (MCP,    │  │
│  │          │  │ (use-cases)    │  │  Graphs)     │  │  DB, LLM)│  │
│  └──────────┘  └────────────────┘  └──────────────┘  └──────────┘  │
│                            │                                       │
│                            ▼                                       │
│                  ┌──────────────────┐                              │
│                  │ LangGraph Runtime│                              │
│                  │  + Checkpointer  │                              │
│                  └────────┬─────────┘                              │
└───────────────────────────┼────────────────────────────────────────┘
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
┌──────────────┐    ┌───────────────┐    ┌────────────────┐
│  Postgres    │    │   Redis       │    │  MCP Servers   │
│  threads,    │    │   pub/sub,    │    │  github, slack,│
│  checkpoints │    │   rate limit  │    │  linear, fs    │
└──────────────┘    └───────────────┘    └────────────────┘
```

## 3. Agent design — Supervisor + Specialists

We use the **Supervisor pattern** in LangGraph (`langgraph.prebuilt.create_supervisor` in spirit, hand-rolled for control). The supervisor reads the user's request, picks a specialist, and delegates. Specialists can hand back to the supervisor or finish.

### Agents

| Agent             | Responsibility                                                | Primary MCP tools                          |
|-------------------|---------------------------------------------------------------|--------------------------------------------|
| `supervisor`      | Routing, planning, final answer composition.                  | none (LLM-only)                            |
| `pr_reviewer`     | Reads diffs, runs static checks, leaves structured feedback.  | github (pulls, files, comments)            |
| `issue_triager`   | Labels, prioritizes, deduplicates issues; suggests assignees. | github (issues), linear (tasks)            |
| `doc_writer`      | Generates or updates README / module docs from source.        | github (files), filesystem                 |
| `code_searcher`   | Semantic + lexical search across repos and docs.              | github (code search), filesystem, vector DB |
| `standup_agent`   | Summarizes activity from PRs, commits, Slack threads.         | github, slack                              |

### Shared graph state

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: Literal["supervisor", "pr_reviewer", ...] | None
    plan: list[PlanStep]                  # produced by supervisor
    artifacts: dict[str, Any]             # tool outputs keyed by step id
    errors: list[AgentError]              # accumulated, never raised through the graph
    interrupt_request: HITLRequest | None # populated when human approval needed
```

### Control flow

1. `supervisor` node receives messages, emits a `plan` and a `route` decision.
2. Conditional edge maps `route` → specialist node OR `__end__`.
3. Specialist runs ReAct loop with its bound tool subset (MCP-mediated).
4. Specialist returns to `supervisor` for either composition or another hop.
5. `supervisor` writes the final answer and ends.

### Patterns layered on top
- **Reflection** — after any specialist tool call, a lightweight critique prompt validates the output before commit.
- **Human-in-the-loop** — destructive tools (closing issues, posting comments) trigger a graph `interrupt()` that the UI surfaces as an approval card.
- **Memory** — short-term via checkpointer; long-term via a `user_profile` summary regenerated on conversation close.

## 4. MCP integration layer

All external capabilities go through MCP. Inside the API we keep a single `MCPRegistry`:

```python
class MCPRegistry:
    async def list_servers(self) -> list[MCPServerInfo]: ...
    async def connect(self, server_id: str, config: MCPServerConfig) -> None: ...
    async def tools_for(self, agent_id: str) -> list[Tool]: ...
    async def call(self, tool_call: ToolCall) -> ToolResult: ...
```

Each agent declares the set of MCP server IDs it is allowed to use. The registry resolves tool names against that allowlist and converts MCP `Tool` definitions into LangChain `BaseTool` shims at startup.

**Why this matters**
- Adding a new connector = adding a new MCP server to the registry; no agent code changes.
- Tool calls are uniformly logged, retried, and rate-limited at the registry boundary.
- Per-agent allowlists give us least-privilege out of the box.

## 5. Backend layering (Hexagonal / Clean Architecture)

```
apps/api/
├── src/devhub/
│   ├── api/            # FastAPI routers, request/response schemas
│   ├── application/    # Use-cases: StartRun, ResumeRun, ListThreads...
│   ├── domain/         # Agents, graphs, value objects (no I/O)
│   ├── adapters/
│   │   ├── llm/        # LangChain LLM providers
│   │   ├── mcp/        # MCPRegistry impl
│   │   ├── persistence/# Postgres repos via SQLAlchemy
│   │   └── streaming/  # SSE writer, Redis pub/sub
│   ├── core/           # Errors, settings, logging, telemetry
│   └── main.py
└── tests/
```

Dependency rule: arrows point **inward**. The domain layer (agents/graphs) does not import from `adapters/*` directly — it receives ports via constructor injection.

## 6. Generic error handling

A single `DevHubError` base with structured subclasses:

```python
class DevHubError(Exception):
    code: str               # stable machine code, e.g. "MCP_TOOL_TIMEOUT"
    http_status: int = 500
    user_message: str       # safe to show end-users
    retriable: bool = False
    cause: Exception | None = None

class ValidationError(DevHubError): ...
class AuthError(DevHubError): ...
class MCPError(DevHubError): ...        # wraps tool failures
class AgentError(DevHubError): ...
class UpstreamError(DevHubError): ...   # LLM provider, GitHub API, etc.
```

### Boundaries
- **Tool boundary (MCP):** every tool call is wrapped in `with_retries(...)` (exponential backoff + jitter, capped) for `retriable=True` errors. Non-retriable errors are converted to a `ToolResult(error=...)` so the agent can self-correct in-loop instead of crashing the run.
- **Graph boundary:** the LangGraph runtime never raises out. Errors flow into `state.errors`. The supervisor reads them and decides: retry, switch tool, escalate to user.
- **HTTP boundary:** FastAPI middleware catches `DevHubError` → emits **RFC 7807** `application/problem+json` with `code`, `title`, `detail`, `traceId`, `retryAfter?`. Unknown exceptions become `500` with a redacted `user_message`.
- **Streaming boundary:** SSE emits a typed `error` event with `{ code, message, retryable }`; the client maps these to retry/dismiss UI.

### Frontend mirror
- Route-level **Error Boundaries** (`error.tsx`) per App Router segment.
- A shared `<AsyncBoundary>` combining `<Suspense>` + `<ErrorBoundary>` for component-level fallbacks.
- A global `apiClient` that parses `problem+json` into a typed `AppError` and feeds the toast system.
- Tool-call cards render their own `error` state with a retry action that re-invokes the tool through the agent.

## 7. Streaming protocol

We use **Server-Sent Events** for run output and a **WebSocket** only for HITL bidirectional approvals. Event types:

```
event: token        # incremental assistant text
event: tool_call    # { id, name, args }
event: tool_result  # { id, ok, data | error }
event: state        # delta of AgentState (current_agent, plan)
event: interrupt    # HITL approval requested
event: error        # typed error
event: done         # run complete
```

The frontend uses Vercel AI SDK's `useChat` with a custom transport that maps these events to UI primitives (message parts, tool cards, etc.).

## 8. Frontend architecture

### Stack
- Next.js 15, App Router, React 19, RSC where useful (thread list, settings).
- Vercel AI SDK v3 (`@ai-sdk/react`) for streaming primitives.
- shadcn/ui + Tailwind v4 for the design system.
- TanStack Query for server cache; Zustand for ephemeral UI state.
- Zod for API schema parsing (generated from FastAPI OpenAPI).
- Playwright for E2E, Vitest + Testing Library for units.

### Layering

```
apps/web/src/
├── app/                         # routes (RSC by default)
│   ├── (chat)/threads/[id]/
│   ├── settings/connections/
│   └── api/                     # BFF route handlers (auth, proxy)
├── features/                    # feature slices (vertical)
│   ├── chat/
│   ├── traces/
│   └── connections/
├── components/                  # cross-feature, presentational
│   └── ui/                      # shadcn primitives
├── lib/
│   ├── api/                     # typed client, problem+json parser
│   ├── streaming/               # SSE transport for AI SDK
│   └── errors/                  # AppError, mapping, toast bus
└── styles/
```

### Patterns
- **Feature-sliced** organization (each feature owns its components, hooks, server actions).
- **Server Components first**, drop to client only when interactivity / streaming is needed.
- **Generative UI** — tool calls map to dedicated React renderers (e.g. `<PRDiffCard>`, `<IssueCard>`).
- **Compound components** for complex widgets (Trace viewer = `<Trace>`, `<Trace.Step>`, `<Trace.Tool>`).
- **State colocation** — server state in TanStack Query; ephemeral UI in Zustand; no Redux.

## 9. Persistence model

```sql
threads(id, user_id, title, created_at, updated_at)
messages(id, thread_id, role, content_jsonb, created_at)
runs(id, thread_id, status, started_at, finished_at, error_jsonb)
checkpoints(id, run_id, step, state_jsonb, created_at)   -- LangGraph checkpointer
mcp_connections(id, user_id, server_id, config_jsonb, status)
audit_log(id, user_id, action, target, payload_jsonb, created_at)
```

LangGraph's `PostgresSaver` writes to `checkpoints`. The same DB hosts business tables — single source of truth, single migration tool (Alembic).

## 10. Security & secrets
- OAuth (GitHub, Slack) for user-scoped MCP connections; tokens stored encrypted (AES-GCM, KMS-managed key).
- Per-agent tool allowlists enforced server-side regardless of what the LLM "tries" to call.
- All HITL-required tools are flagged in metadata; the registry refuses to execute them without an `approval_id`.
- Rate limits: per-user, per-tool, and per-MCP-server.

## 11. Observability
- **LangSmith** — every graph run is traced; `LANGCHAIN_TRACING_V2=true`.
- **Sentry** — frontend + backend exception capture with `traceId` correlation to LangSmith.
- **OpenTelemetry** — spans across HTTP → use-case → tool call; exported to whatever the team picks (Honeycomb / Tempo).
- **Structured logs** — JSON, with `trace_id`, `run_id`, `agent`, `tool`.

## 12. Local dev

`docker compose up` brings up Postgres, Redis, the API, and one or two MCP servers. The web app runs on the host via `pnpm dev` for fast HMR. A single `make seed` populates demo threads.

## 13. Deployment (later)
- Frontend → Vercel.
- API → Fly.io or Render (long-lived workers for streaming).
- Postgres → Neon / RDS; Redis → Upstash / ElastiCache.
- MCP servers run as sidecar containers next to the API.

## 14. Architecture Decision Records
ADRs live in `docs/ADRs/`. Required for: choice of LLM provider, agent topology changes, new MCP servers, persistence schema changes.
