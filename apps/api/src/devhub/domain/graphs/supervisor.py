"""Supervisor LangGraph — routes to specialist agents.

Build:
    graph = build_supervisor_graph(llm, mcp_registry=registry)
    compiled = graph.compile(checkpointer=saver)

The supervisor node calls the LLM to decide the route.  Specialists return
to the supervisor after completing their work; the supervisor then decides
whether to route again or end.

Error contract: no node raises out of the graph. All exceptions are caught,
appended to ``state["errors"]``, and the graph ends gracefully.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from devhub.domain.agent_state import AgentErrorRecord, AgentState
from devhub.domain.agents.code_searcher import make_code_searcher_node
from devhub.domain.agents.doc_writer import make_doc_writer_node
from devhub.domain.agents.issue_triager import make_issue_triager_node
from devhub.domain.agents.pr_reviewer import make_pr_reviewer_node
from devhub.domain.ports import ILLMPort, IMCPRegistry, IVectorStore

_SUPERVISOR_PROMPT = (
    pathlib.Path(__file__).parent.parent / "prompts" / "supervisor.md"
).read_text()

_ROUTE_ECHO = "echo_specialist"
_ROUTE_PR_REVIEWER = "pr_reviewer"
_ROUTE_ISSUE_TRIAGER = "issue_triager"
_ROUTE_DOC_WRITER = "doc_writer"
_ROUTE_CODE_SEARCHER = "code_searcher"
_ROUTE_DONE = "__end__"

_VALID_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    {_ROUTE_ECHO, _ROUTE_PR_REVIEWER, _ROUTE_ISSUE_TRIAGER, _ROUTE_DOC_WRITER, _ROUTE_CODE_SEARCHER}
)


def _make_supervisor(llm: ILLMPort) -> Callable[[AgentState], Any]:
    async def supervisor(state: AgentState) -> Command[str]:
        # If a specialist already responded (last message is AIMessage), end the loop.
        messages = list(state["messages"])
        if messages and isinstance(messages[-1], AIMessage):
            return Command(goto=END, update={"current_agent": None})

        try:
            response = await llm.chat(
                messages,
                system=_SUPERVISOR_PROMPT,
            )
            content = response.content
            route = _parse_route(content if isinstance(content, str) else "")
        except Exception as exc:
            error = AgentErrorRecord(
                code="AGENT_ERROR",
                message=str(exc),
                agent="supervisor",
                retryable=False,
            )
            fallback = AIMessage(content="I encountered an error. Please try again.")
            return Command(
                goto=END,
                update={
                    "messages": [fallback],
                    "current_agent": None,
                    "errors": [error],
                },
            )

        if route == _ROUTE_DONE:
            return Command(goto=END, update={"current_agent": None})

        return Command(
            goto=route,
            update={"current_agent": route},
        )

    return supervisor


def _make_echo_specialist(llm: ILLMPort) -> Callable[[AgentState], Any]:
    async def echo_specialist(state: AgentState) -> Command[str]:
        try:
            last_human = next(
                (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
                None,
            )
            text = last_human.content if last_human else "(no message)"
            reply = AIMessage(content=f"[echo] {text}")
            return Command(
                goto="supervisor",
                update={"messages": [reply], "current_agent": "supervisor"},
            )
        except Exception as exc:
            error = AgentErrorRecord(
                code="AGENT_ERROR",
                message=str(exc),
                agent="echo_specialist",
                retryable=False,
            )
            return Command(
                goto="supervisor",
                update={"errors": [error], "current_agent": "supervisor"},
            )

    return echo_specialist


def _parse_route(content: str) -> str:
    """Extract route from supervisor LLM response.

    Accepts a JSON line ``{"route": "...", "reasoning": "..."}`` or falls back
    to ``echo_specialist`` if parsing fails or the route is unknown.
    """
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            route = str(data.get("route", _ROUTE_ECHO))
            if route.upper() == "DONE":
                return _ROUTE_DONE
            if route in _VALID_SPECIALIST_ROUTES:
                return route
    except (json.JSONDecodeError, KeyError):
        pass
    return _ROUTE_ECHO


def build_supervisor_graph(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None = None,
    vector_store: IVectorStore | None = None,
) -> StateGraph:  # type: ignore[type-arg]
    """Return an uncompiled graph — caller adds the checkpointer at compile time.

    ``mcp_registry`` is forwarded to specialist nodes for lazy tool fetching.
    ``vector_store`` is forwarded to code_searcher for semantic retrieval.
    Pass ``None`` for either in tests or degraded mode.
    """
    builder: StateGraph[AgentState] = StateGraph(AgentState)

    builder.add_node("supervisor", _make_supervisor(llm))  # type: ignore[call-overload]
    builder.add_node(_ROUTE_ECHO, _make_echo_specialist(llm))  # type: ignore[call-overload]
    builder.add_node(  # type: ignore[call-overload]
        _ROUTE_PR_REVIEWER,
        make_pr_reviewer_node(llm, mcp_registry),
    )
    builder.add_node(  # type: ignore[call-overload]
        _ROUTE_ISSUE_TRIAGER,
        make_issue_triager_node(llm, mcp_registry),
    )
    builder.add_node(  # type: ignore[call-overload]
        _ROUTE_DOC_WRITER,
        make_doc_writer_node(llm, mcp_registry),
    )
    builder.add_node(  # type: ignore[call-overload]
        _ROUTE_CODE_SEARCHER,
        make_code_searcher_node(llm, mcp_registry, vector_store),
    )

    builder.add_edge(START, "supervisor")

    return builder


def compile_supervisor_graph(
    llm: ILLMPort,
    checkpointer: BaseCheckpointSaver,  # type: ignore[type-arg]
    mcp_registry: IMCPRegistry | None = None,
    vector_store: IVectorStore | None = None,
) -> Any:
    """Compile the supervisor graph with the given checkpointer."""
    return build_supervisor_graph(
        llm, mcp_registry=mcp_registry, vector_store=vector_store
    ).compile(checkpointer=checkpointer)
