"""Tests for the LangGraph supervisor skeleton.

All tests run against MemorySaver — no real Postgres needed.
Integration tests that require Postgres are marked @pytest.mark.integration.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from devhub.application.use_cases.run_events import DoneEvent, ErrorEvent
from devhub.application.use_cases.start_run import StartRunUseCase
from devhub.domain.graphs.supervisor import build_supervisor_graph
from devhub.domain.models import Run
from devhub.domain.ports import IRunRepository

# ── Fake LLM ─────────────────────────────────────────────────────────────────


class _RoutingFakeLLM:
    """Returns a fixed routing sequence: echo_specialist → DONE."""

    def __init__(self, routes: list[str]) -> None:
        self._routes = iter(routes)

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, messages: list[BaseMessage], *, system: str | None = None) -> AIMessage:
        try:
            route = next(self._routes)
        except StopIteration:
            route = "DONE"
        return AIMessage(content=f'{{"route": "{route}", "reasoning": "test"}}')


class _ErrorFakeLLM:
    """Raises on the first call to simulate supervisor failure."""

    async def is_healthy(self) -> bool:
        return True

    async def chat(self, messages: list[BaseMessage], *, system: str | None = None) -> AIMessage:
        raise RuntimeError("LLM service unavailable")


# ── Fake RunRepository ────────────────────────────────────────────────────────


class _FakeRunRepo:
    """In-memory run repository."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, Run] = {}

    async def create(self, thread_id: uuid.UUID) -> Run:
        from datetime import UTC, datetime

        run = Run(
            id=uuid.uuid4(),
            thread_id=thread_id,
            status="running",
            started_at=datetime.now(UTC),
        )
        self._runs[run.id] = run
        return run

    async def get(self, run_id: uuid.UUID) -> Run | None:
        return self._runs.get(run_id)

    async def mark_completed(self, run_id: uuid.UUID) -> None:
        run = self._runs[run_id]
        self._runs[run_id] = run.model_copy(update={"status": "completed"})

    async def mark_failed(self, run_id: uuid.UUID, error_data: dict[str, object]) -> None:
        run = self._runs[run_id]
        self._runs[run_id] = run.model_copy(update={"status": "failed", "error_data": error_data})


assert isinstance(_FakeRunRepo(), IRunRepository)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_graph(llm: Any) -> Any:
    return build_supervisor_graph(llm).compile(checkpointer=MemorySaver())


async def _collect(it: AsyncIterator[Any]) -> list[Any]:
    return [e async for e in it]


# ── Tests: graph logic ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_graph_routes_through_echo_specialist() -> None:
    llm = _RoutingFakeLLM(["echo_specialist"])
    graph = _make_graph(llm)
    thread_id = str(uuid.uuid4())

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Hello!")], "errors": [], "plan": [], "artifacts": {}},
        config={"configurable": {"thread_id": thread_id}},
    )

    messages = result["messages"]
    contents = [m.content for m in messages]
    assert any("[echo] Hello!" in c for c in contents)


@pytest.mark.asyncio
async def test_graph_accumulates_errors_from_failing_supervisor() -> None:
    llm = _ErrorFakeLLM()
    graph = _make_graph(llm)
    thread_id = str(uuid.uuid4())

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Hi")], "errors": [], "plan": [], "artifacts": {}},
        config={"configurable": {"thread_id": thread_id}},
    )

    assert len(result["errors"]) > 0
    assert result["errors"][0].code == "AGENT_ERROR"


@pytest.mark.asyncio
async def test_graph_never_raises_on_llm_failure() -> None:
    """Graph must complete even when the LLM is broken."""
    llm = _ErrorFakeLLM()
    graph = _make_graph(llm)
    thread_id = str(uuid.uuid4())

    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Crash me")], "errors": [], "plan": [], "artifacts": {}},
        config={"configurable": {"thread_id": thread_id}},
    )
    assert "messages" in result


@pytest.mark.asyncio
async def test_graph_resumes_from_checkpoint() -> None:
    llm = _RoutingFakeLLM(["echo_specialist"])
    graph = _make_graph(llm)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # First run
    await graph.ainvoke(
        {"messages": [HumanMessage(content="First")], "errors": [], "plan": [], "artifacts": {}},
        config=config,
    )

    # Resume — send a second message to the same thread
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="Second")]},
        config=config,
    )
    contents = [m.content for m in result["messages"]]
    assert any("Second" in c for c in contents)


# ── Tests: StartRun use-case ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_run_yields_done_event() -> None:
    llm = _RoutingFakeLLM(["echo_specialist"])
    graph = _make_graph(llm)
    run_repo = _FakeRunRepo()
    use_case = StartRunUseCase(graph, run_repo)

    thread_id = uuid.uuid4()
    events = await _collect(await use_case.execute(thread_id, "Say hi"))

    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done_events) == 1
    assert done_events[0].run_id is not None


@pytest.mark.asyncio
async def test_start_run_marks_run_completed() -> None:
    llm = _RoutingFakeLLM(["echo_specialist"])
    graph = _make_graph(llm)
    run_repo = _FakeRunRepo()
    use_case = StartRunUseCase(graph, run_repo)

    thread_id = uuid.uuid4()
    events = await _collect(await use_case.execute(thread_id, "Hello"))

    done = next(e for e in events if isinstance(e, DoneEvent))
    run = await run_repo.get(done.run_id)
    assert run is not None
    assert run.status == "completed"


@pytest.mark.asyncio
async def test_start_run_surfaces_error_events_on_node_failure() -> None:
    """Tool failure inside a node → ErrorEvent emitted, run still completes."""
    llm = _ErrorFakeLLM()
    graph = _make_graph(llm)
    run_repo = _FakeRunRepo()
    use_case = StartRunUseCase(graph, run_repo)

    thread_id = uuid.uuid4()
    events = await _collect(await use_case.execute(thread_id, "Break things"))

    error_events = [e for e in events if isinstance(e, ErrorEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(error_events) > 0
    assert len(done_events) == 1
