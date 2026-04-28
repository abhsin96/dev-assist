"""Supervisor LangGraph — skeleton with one placeholder specialist.

Build:
    graph = build_supervisor_graph(llm)
    compiled = graph.compile(checkpointer=saver)

The supervisor node calls the LLM to decide the route. The echo_specialist
is a placeholder that echoes the last human message back; real specialists
(DEVHUB-011 +) will replace / join it.

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
from devhub.domain.ports import ILLMPort

_SUPERVISOR_PROMPT = (
    pathlib.Path(__file__).parent.parent / "prompts" / "supervisor.md"
).read_text()

_ROUTE_ECHO = "echo_specialist"
_ROUTE_DONE = "__end__"


def _make_supervisor(llm: ILLMPort) -> Callable[[AgentState], Any]:
    async def supervisor(state: AgentState) -> Command[str]:
        try:
            response = await llm.chat(
                list(state["messages"]),
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
    to ``echo_specialist`` if parsing fails.
    """
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            route = str(data.get("route", _ROUTE_ECHO))
            return _ROUTE_DONE if route.upper() == "DONE" else route
    except (json.JSONDecodeError, KeyError):
        pass
    return _ROUTE_ECHO


def build_supervisor_graph(llm: ILLMPort) -> StateGraph:  # type: ignore[type-arg]
    """Return an uncompiled graph — caller adds the checkpointer at compile time."""
    builder: StateGraph[AgentState] = StateGraph(AgentState)

    builder.add_node("supervisor", _make_supervisor(llm))  # type: ignore[call-overload]
    builder.add_node(_ROUTE_ECHO, _make_echo_specialist(llm))  # type: ignore[call-overload]

    builder.add_edge(START, "supervisor")

    return builder


def compile_supervisor_graph(
    llm: ILLMPort,
    checkpointer: BaseCheckpointSaver,  # type: ignore[type-arg]
) -> Any:
    """Compile the supervisor graph with the given checkpointer."""
    return build_supervisor_graph(llm).compile(checkpointer=checkpointer)
