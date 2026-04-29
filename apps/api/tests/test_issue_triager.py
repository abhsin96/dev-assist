"""Unit tests for the Issue Triager specialist agent.

All tests use a fake MCP registry and a fake LLM — no real network calls or
Anthropic API key needed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from devhub.domain.agent_state import AgentState
from devhub.domain.agents.issue_triager import (
    _cache_key,
    _detect_duplicate,
    _extract_label_filter,
    _extract_repo,
    _jaccard_similarity,
    _parse_triage,
    make_issue_triager_node,
)
from devhub.domain.models import IssueTriage
from devhub.domain.ports import IMCPRegistry

# ── Fake infrastructure ───────────────────────────────────────────────────────


class _FakeTool(BaseTool):
    name: str
    description: str = "fake tool"
    _response: str

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name: str, response: str) -> None:
        super().__init__(name=name, description="fake tool")
        object.__setattr__(self, "_response", response)

    def _run(self, *args: Any, **kwargs: Any) -> str:  # noqa: ARG002
        raise NotImplementedError("sync not supported")

    async def _arun(self, *args: Any, **kwargs: Any) -> str:  # noqa: ARG002
        return self._response


class _FakeMCPRegistry:
    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = tools

    async def tools_for(self, agent_id: str) -> list[BaseTool]:  # noqa: ARG002
        return self._tools

    async def connect(self, config: Any) -> None: ...  # noqa: ANN401
    async def disconnect(self, server_id: str) -> None: ...
    async def list_servers(self) -> list[Any]:
        return []

    async def call(self, tool_call: Any) -> Any: ...  # noqa: ANN401
    async def is_healthy(self) -> bool:
        return True


assert isinstance(_FakeMCPRegistry([]), IMCPRegistry)


class _FakeLLM:
    """Returns canned responses in order; loops on the last one when exhausted."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._idx = 0

    async def chat(
        self,
        messages: list[BaseMessage],  # noqa: ARG002
        *,
        system: str | None = None,  # noqa: ARG002
    ) -> AIMessage:
        content = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return AIMessage(content=content)


# ── Test fixtures ─────────────────────────────────────────────────────────────

_REPO_URL = "https://github.com/myorg/myrepo"

# Issue 1 and 2 are intentionally similar (login button) to trigger duplicate detection.
_ISSUE_1 = {
    "number": 1,
    "title": "Login button not working on mobile",
    "body": "The login button does not respond when clicked on mobile devices.",
    "state": "open",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "user": {"login": "alice"},
    "labels": [],
}
_ISSUE_2 = {
    "number": 2,
    "title": "Login button broken on mobile devices",
    "body": "The login button is not working on mobile.",
    "state": "open",
    "created_at": "2024-01-03T00:00:00Z",
    "updated_at": "2024-01-04T00:00:00Z",
    "user": {"login": "bob"},
    "labels": [],
}
_ISSUE_3 = {
    "number": 3,
    "title": "Add dark mode support",
    "body": "Feature request: please add a dark mode theme option to the application.",
    "state": "open",
    "created_at": "2024-01-05T00:00:00Z",
    "updated_at": "2024-01-06T00:00:00Z",
    "user": {"login": "carol"},
    "labels": [],
}

_TRIAGE_P1_JSON = json.dumps(
    {
        "priority": "P1",
        "labels": ["bug"],
        "duplicate_of": None,
        "suggested_assignee": None,
        "rationale": "Login button not working — significant UX regression.",
    }
)
_TRIAGE_P2_DUP_JSON = json.dumps(
    {
        "priority": "P2",
        "labels": [],
        "duplicate_of": 1,
        "suggested_assignee": None,
        "rationale": "Duplicate of #1.",
    }
)
_TRIAGE_P3_JSON = json.dumps(
    {
        "priority": "P3",
        "labels": ["enhancement"],
        "duplicate_of": None,
        "suggested_assignee": None,
        "rationale": "Feature request with low urgency.",
    }
)
_TRIAGE_NO_MUTATIONS_JSON = json.dumps(
    {
        "priority": "P2",
        "labels": [],
        "duplicate_of": None,
        "suggested_assignee": None,
        "rationale": "Informational — no action required.",
    }
)


def _make_state(content: str = f"Triage issues in {_REPO_URL}") -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=content)],
        current_agent="issue_triager",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )


def _issues_tool(*issues: dict[str, Any]) -> _FakeTool:
    return _FakeTool("list_issues", json.dumps(list(issues)))


# ── Pure helper tests ─────────────────────────────────────────────────────────


def test_extract_repo_from_github_url() -> None:
    msgs = [HumanMessage(content=f"Triage issues in {_REPO_URL}")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_from_bare_notation() -> None:
    msgs = [HumanMessage(content="Triage myorg/myrepo please")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_returns_none_when_missing() -> None:
    assert _extract_repo([HumanMessage(content="What is the weather?")]) is None


def test_extract_label_filter_space_syntax() -> None:
    msgs = [HumanMessage(content="Triage issues labeled bug in myorg/myrepo")]
    assert _extract_label_filter(msgs) == "bug"


def test_extract_label_filter_colon_syntax() -> None:
    msgs = [HumanMessage(content="Triage myorg/myrepo label:enhancement")]
    assert _extract_label_filter(msgs) == "enhancement"


def test_extract_label_filter_none_when_absent() -> None:
    assert _extract_label_filter([HumanMessage(content="Triage myorg/myrepo")]) is None


def test_jaccard_similarity_identical() -> None:
    assert _jaccard_similarity("hello world", "hello world") == pytest.approx(1.0)


def test_jaccard_similarity_disjoint() -> None:
    assert _jaccard_similarity("hello world", "foo bar") == pytest.approx(0.0)


def test_jaccard_similarity_partial() -> None:
    score = _jaccard_similarity("login button broken", "login button works")
    assert 0.0 < score < 1.0


def test_detect_duplicate_finds_similar_issue() -> None:
    duplicate = _detect_duplicate(_ISSUE_2, [_ISSUE_1, _ISSUE_2])
    assert duplicate == 1


def test_detect_duplicate_no_match_for_distinct_issue() -> None:
    assert _detect_duplicate(_ISSUE_3, [_ISSUE_1, _ISSUE_3]) is None


def test_detect_duplicate_skips_same_issue() -> None:
    assert _detect_duplicate(_ISSUE_1, [_ISSUE_1]) is None


def test_cache_key_is_deterministic() -> None:
    k1 = _cache_key("myorg", "myrepo", 1, "2024-01-02T00:00:00Z")
    k2 = _cache_key("myorg", "myrepo", 1, "2024-01-02T00:00:00Z")
    assert k1 == k2


def test_cache_key_differs_on_updated_at() -> None:
    k1 = _cache_key("myorg", "myrepo", 1, "2024-01-02T00:00:00Z")
    k2 = _cache_key("myorg", "myrepo", 1, "2024-01-03T00:00:00Z")
    assert k1 != k2


def test_parse_triage_valid_json() -> None:
    triage = _parse_triage(_TRIAGE_P1_JSON, 1, "Login button not working on mobile")
    assert isinstance(triage, IssueTriage)
    assert triage.priority == "P1"
    assert triage.labels == ["bug"]
    assert triage.duplicate_of is None


def test_parse_triage_falls_back_on_bad_json() -> None:
    triage = _parse_triage("not json", 5, "Some issue")
    assert triage.issue_number == 5
    assert triage.priority == "P3"
    assert triage.labels == []


def test_parse_triage_normalizes_invalid_priority() -> None:
    data = json.dumps({"priority": "CRITICAL", "labels": [], "rationale": "x"})
    triage = _parse_triage(data, 1, "t")
    assert triage.priority == "P3"


# ── Integration tests: node function ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_triage_produces_result_for_single_issue() -> None:
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    llm = _FakeLLM([_TRIAGE_P3_JSON])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    assert command.goto == "supervisor"
    body = json.loads(command.update["messages"][0].content)
    assert body["owner"] == "myorg"
    assert body["repo"] == "myrepo"
    assert len(body["triaged"]) == 1
    assert body["triaged"][0]["priority"] == "P3"


@pytest.mark.asyncio
async def test_triage_with_label_mutation_creates_hitl() -> None:
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_1)])
    llm = _FakeLLM([_TRIAGE_P1_JSON])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    hitl = command.update.get("interrupt_request")
    assert hitl is not None
    assert hitl.tool_name == "apply_issue_triage_batch"
    assert hitl.tool_args["owner"] == "myorg"
    assert len(hitl.tool_args["mutations"]) == 1


@pytest.mark.asyncio
async def test_triage_no_hitl_when_no_mutations() -> None:
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    llm = _FakeLLM([_TRIAGE_NO_MUTATIONS_JSON])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    assert command.update.get("interrupt_request") is None


@pytest.mark.asyncio
async def test_triage_duplicate_confirmed_by_llm() -> None:
    """Issue 2 flagged as duplicate of 1 by Jaccard; LLM confirms."""
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_1, _ISSUE_2)])
    llm = _FakeLLM([_TRIAGE_P1_JSON, _TRIAGE_P2_DUP_JSON])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    body = json.loads(command.update["messages"][0].content)
    triaged = body["triaged"]
    assert len(triaged) == 2
    issue2 = next(t for t in triaged if t["issue_number"] == 2)
    assert issue2["duplicate_of"] == 1


@pytest.mark.asyncio
async def test_triage_respects_cache_on_unchanged_issue() -> None:
    """Same updated_at → cache hit; LLM must NOT be called on the second run."""
    call_count = 0

    class _CountingLLM:
        async def chat(
            self, messages: list[BaseMessage], *, system: str | None = None
        ) -> AIMessage:
            nonlocal call_count
            call_count += 1
            return AIMessage(content=_TRIAGE_P3_JSON)

    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    node = make_issue_triager_node(_CountingLLM(), registry)

    command1 = await node(_make_state())
    assert call_count == 1

    state_with_cache = AgentState(
        messages=[HumanMessage(content=f"Triage issues in {_REPO_URL}")],
        current_agent="issue_triager",
        plan=[],
        artifacts=command1.update.get("artifacts", {}),
        errors=[],
        interrupt_request=None,
    )
    await node(state_with_cache)
    assert call_count == 1  # no additional LLM call


@pytest.mark.asyncio
async def test_cache_invalidates_on_updated_at_change() -> None:
    """Changed updated_at must bust the cache and call the LLM again."""
    call_count = 0

    class _CountingLLM:
        async def chat(
            self, messages: list[BaseMessage], *, system: str | None = None
        ) -> AIMessage:
            nonlocal call_count
            call_count += 1
            return AIMessage(content=_TRIAGE_P3_JSON)

    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    node = make_issue_triager_node(_CountingLLM(), registry)
    command1 = await node(_make_state())
    assert call_count == 1

    updated_issue = {**_ISSUE_3, "updated_at": "2024-02-01T00:00:00Z"}
    registry2 = _FakeMCPRegistry([_issues_tool(updated_issue)])
    node2 = make_issue_triager_node(_CountingLLM(), registry2)
    state_with_cache = AgentState(
        messages=[HumanMessage(content=f"Triage issues in {_REPO_URL}")],
        current_agent="issue_triager",
        plan=[],
        artifacts=command1.update.get("artifacts", {}),
        errors=[],
        interrupt_request=None,
    )
    await node2(state_with_cache)
    assert call_count == 2


@pytest.mark.asyncio
async def test_missing_repo_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry([])
    llm = _FakeLLM([])
    node = make_issue_triager_node(llm, registry)

    state = AgentState(
        messages=[HumanMessage(content="Please triage my issues")],
        current_agent="issue_triager",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )
    command = await node(state)
    assert command.goto == "supervisor"
    reply = command.update["messages"][0].content
    assert "github" in reply.lower() or "repository" in reply.lower()


@pytest.mark.asyncio
async def test_empty_issue_list_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry([_FakeTool("list_issues", json.dumps([]))])
    llm = _FakeLLM([])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    reply = command.update["messages"][0].content
    assert "no open issues" in reply.lower()


@pytest.mark.asyncio
async def test_triage_result_stored_in_artifacts() -> None:
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    llm = _FakeLLM([_TRIAGE_P3_JSON])
    node = make_issue_triager_node(llm, registry)

    command = await node(_make_state())
    artifacts = command.update.get("artifacts", {})
    assert "issue_triage" in artifacts
    assert "triaged" in artifacts["issue_triage"]
    assert artifacts["issue_triage"]["owner"] == "myorg"


@pytest.mark.asyncio
async def test_cache_hits_counter_increments_on_cache_reuse() -> None:
    registry = _FakeMCPRegistry([_issues_tool(_ISSUE_3)])
    llm = _FakeLLM([_TRIAGE_P3_JSON])
    node = make_issue_triager_node(llm, registry)

    command1 = await node(_make_state())
    state_with_cache = AgentState(
        messages=[HumanMessage(content=f"Triage issues in {_REPO_URL}")],
        current_agent="issue_triager",
        plan=[],
        artifacts=command1.update.get("artifacts", {}),
        errors=[],
        interrupt_request=None,
    )
    command2 = await node(state_with_cache)
    body = json.loads(command2.update["messages"][0].content)
    assert body["cache_hits"] == 1


@pytest.mark.asyncio
async def test_node_never_raises_on_registry_error() -> None:
    class _BrokenRegistry:
        async def tools_for(self, agent_id: str) -> list[BaseTool]:
            raise RuntimeError("registry exploded")

        async def connect(self, config: Any) -> None: ...
        async def disconnect(self, server_id: str) -> None: ...
        async def list_servers(self) -> list[Any]:
            return []

        async def call(self, tool_call: Any) -> Any: ...
        async def is_healthy(self) -> bool:
            return False

    node = make_issue_triager_node(_FakeLLM([]), _BrokenRegistry())  # type: ignore[arg-type]
    command = await node(_make_state())

    assert command.goto == "supervisor"
    errors = command.update.get("errors", [])
    assert len(errors) == 1
    assert errors[0].code == "AGENT_ERROR"
    assert errors[0].agent == "issue_triager"
