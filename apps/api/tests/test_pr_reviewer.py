"""Unit tests for the PR Reviewer specialist agent.

All tests use a fake MCP registry (recorded transport) and a fake LLM —
no real network calls or Anthropic API key needed.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from devhub.domain.agent_state import AgentState
from devhub.domain.agents.pr_reviewer import (
    _MAX_DIFF_CHARS,
    _apply_reflection,
    _extract_pr_url,
    _find_sensitive_paths,
    _parse_review,
    make_pr_reviewer_node,
)
from devhub.domain.models import PRReview
from devhub.domain.ports import IMCPRegistry

# ── Fake MCP transport ────────────────────────────────────────────────────────


class _FakeTool(BaseTool):
    """Tool that returns a canned string response."""

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
    """Fake registry that returns pre-built tools."""

    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = tools

    async def tools_for(self, agent_id: str) -> list[BaseTool]:  # noqa: ARG002
        return self._tools

    # Satisfy the IMCPRegistry structural check for remaining stubs
    async def connect(self, config: Any) -> None: ...  # noqa: ANN401
    async def disconnect(self, server_id: str) -> None: ...
    async def list_servers(self) -> list[Any]:
        return []

    async def call(self, tool_call: Any) -> Any: ...  # noqa: ANN401
    async def is_healthy(self) -> bool:
        return True


assert isinstance(_FakeMCPRegistry([]), IMCPRegistry)


# ── Fake LLM ──────────────────────────────────────────────────────────────────


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


# ── Helpers ───────────────────────────────────────────────────────────────────

_PR_URL = "https://github.com/myorg/myrepo/pull/42"

_CLEAN_REVIEW_JSON = json.dumps(
    {
        "summary": "Adds a new utility function.",
        "blocking": [],
        "non_blocking": ["Consider adding a docstring."],
        "nits": ["Variable name could be clearer."],
        "suggested_comment": "Looks good, nice work!",
    }
)

_SECURITY_REVIEW_JSON = json.dumps(
    {
        "summary": "Modifies authentication logic.",
        "blocking": ["JWT secret is now hardcoded — serious security risk."],
        "non_blocking": [],
        "nits": [],
        "suggested_comment": "Please remove the hardcoded secret.",
    }
)

_REFLECTION_JSON = json.dumps(
    {
        "validated_blocking": ["JWT secret is now hardcoded — serious security risk."],
        "false_positives": [],
        "additional_blocking": [],
    }
)

_SMALL_DIFF = "- old line\n+ new line\n"
_FILES_CLEAN = json.dumps([{"filename": "src/utils.py"}])
_FILES_SECURITY = json.dumps([{"filename": "src/auth/jwt.py"}])
_PR_META = json.dumps({"title": "Add utility", "body": ""})


def _make_state(pr_url: str = _PR_URL) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=f"Review this PR: {pr_url}")],
        current_agent="pr_reviewer",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )


def _clean_tools() -> list[BaseTool]:
    return [
        _FakeTool("get_pull_request_diff", _SMALL_DIFF),
        _FakeTool("get_pull_request_files", _FILES_CLEAN),
        _FakeTool("get_pull_request", _PR_META),
    ]


def _security_tools() -> list[BaseTool]:
    return [
        _FakeTool("get_pull_request_diff", _SMALL_DIFF),
        _FakeTool("get_pull_request_files", _FILES_SECURITY),
        _FakeTool("get_pull_request", _PR_META),
    ]


# ── Unit tests: pure helpers ──────────────────────────────────────────────────


def test_extract_pr_url_from_message() -> None:
    messages = [HumanMessage(content=f"Review {_PR_URL} please")]
    result = _extract_pr_url(messages)
    assert result == ("myorg", "myrepo", "42")


def test_extract_pr_url_returns_none_when_missing() -> None:
    assert _extract_pr_url([HumanMessage(content="hello")]) is None


def test_find_sensitive_paths_detects_auth() -> None:
    files_raw = json.dumps(
        [
            {"filename": "src/auth/jwt.py"},
            {"filename": "src/utils.py"},
        ]
    )
    sensitive = _find_sensitive_paths(files_raw)
    assert "src/auth/jwt.py" in sensitive
    assert "src/utils.py" not in sensitive


def test_find_sensitive_paths_detects_env_file() -> None:
    files_raw = json.dumps([{"filename": ".env.production"}])
    sensitive = _find_sensitive_paths(files_raw)
    assert len(sensitive) == 1


def test_parse_review_valid_json() -> None:
    review = _parse_review(_CLEAN_REVIEW_JSON)
    assert isinstance(review, PRReview)
    assert review.summary == "Adds a new utility function."
    assert review.blocking == []
    assert len(review.non_blocking) == 1
    assert review.suggested_comment == "Looks good, nice work!"


def test_parse_review_falls_back_on_bad_json() -> None:
    review = _parse_review("not json at all")
    assert review.summary == "not json at all"
    assert review.blocking == []


def test_apply_reflection_merges_additional_blocking() -> None:
    base = PRReview(
        summary="s",
        blocking=["original"],
        non_blocking=[],
        nits=[],
        suggested_comment="",
    )
    reflection = json.dumps(
        {
            "validated_blocking": ["original"],
            "false_positives": [],
            "additional_blocking": ["new issue found"],
        }
    )
    result = _apply_reflection(base, reflection)
    assert "original" in result.blocking
    assert "new issue found" in result.blocking


def test_apply_reflection_removes_false_positives() -> None:
    base = PRReview(
        summary="s",
        blocking=["real issue", "false alarm"],
        non_blocking=[],
        nits=[],
        suggested_comment="",
    )
    reflection = json.dumps(
        {
            "validated_blocking": ["real issue"],
            "false_positives": ["false alarm"],
            "additional_blocking": [],
        }
    )
    result = _apply_reflection(base, reflection)
    assert "real issue" in result.blocking
    assert "false alarm" not in result.blocking


# ── Integration tests: node function ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_clean_pr_produces_review_with_no_blocking() -> None:
    registry = _FakeMCPRegistry(_clean_tools())
    llm = _FakeLLM([_CLEAN_REVIEW_JSON])
    node = make_pr_reviewer_node(llm, registry)

    state = _make_state()
    command = await node(state)

    assert command.goto == "supervisor"
    messages = command.update.get("messages", [])
    assert len(messages) == 1
    body = json.loads(messages[0].content)
    assert body["blocking"] == []
    assert body["summary"] == "Adds a new utility function."


@pytest.mark.asyncio
async def test_clean_pr_sets_hitl_for_suggested_comment() -> None:
    """Comment posting must be gated by HITL — never auto-posted."""
    registry = _FakeMCPRegistry(_clean_tools())
    llm = _FakeLLM([_CLEAN_REVIEW_JSON])
    node = make_pr_reviewer_node(llm, registry)

    command = await node(_make_state())

    hitl = command.update.get("interrupt_request")
    assert hitl is not None
    assert hitl.tool_name == "create_pull_request_review"
    assert "42" in hitl.prompt  # PR number appears in the approval prompt


@pytest.mark.asyncio
async def test_security_sensitive_change_is_blocking() -> None:
    """Changes to auth paths must produce a blocking item after reflection."""
    registry = _FakeMCPRegistry(_security_tools())
    # First call: review (has blocking); second call: reflection (validates it)
    llm = _FakeLLM([_SECURITY_REVIEW_JSON, _REFLECTION_JSON])
    node = make_pr_reviewer_node(llm, registry)

    command = await node(_make_state())

    body = json.loads(command.update["messages"][0].content)
    assert len(body["blocking"]) > 0
    assert any("JWT" in item or "secret" in item.lower() for item in body["blocking"])


@pytest.mark.asyncio
async def test_oversized_diff_is_truncated() -> None:
    """Diffs beyond _MAX_DIFF_CHARS must be truncated; review notes incompleteness."""
    big_diff = "x" * (_MAX_DIFF_CHARS + 1000)
    tools = [
        _FakeTool("get_pull_request_diff", big_diff),
        _FakeTool("get_pull_request_files", _FILES_CLEAN),
        _FakeTool("get_pull_request", _PR_META),
    ]
    registry = _FakeMCPRegistry(tools)

    # Capture the prompt that the LLM receives so we can inspect truncation note
    received_prompts: list[str] = []

    class _CapturingLLM:
        async def chat(
            self, messages: list[BaseMessage], *, system: str | None = None
        ) -> AIMessage:
            for msg in messages:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    received_prompts.append(msg.content)
            return AIMessage(content=_CLEAN_REVIEW_JSON)

    node = make_pr_reviewer_node(_CapturingLLM(), registry)  # type: ignore[arg-type]
    await node(_make_state())

    assert any("truncated" in p.lower() for p in received_prompts)


@pytest.mark.asyncio
async def test_missing_pr_url_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry(_clean_tools())
    llm = _FakeLLM([_CLEAN_REVIEW_JSON])
    node = make_pr_reviewer_node(llm, registry)

    state = AgentState(
        messages=[HumanMessage(content="Can you review my code?")],
        current_agent="pr_reviewer",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )
    command = await node(state)

    assert command.goto == "supervisor"
    reply = command.update["messages"][0].content
    assert "github.com" in reply.lower() or "url" in reply.lower()


@pytest.mark.asyncio
async def test_pr_review_stored_in_artifacts() -> None:
    registry = _FakeMCPRegistry(_clean_tools())
    llm = _FakeLLM([_CLEAN_REVIEW_JSON])
    node = make_pr_reviewer_node(llm, registry)

    command = await node(_make_state())

    artifacts = command.update.get("artifacts", {})
    assert "pr_review" in artifacts
    assert "summary" in artifacts["pr_review"]


@pytest.mark.asyncio
async def test_node_never_raises_on_registry_error() -> None:
    """Any exception must be caught and returned as an error record."""

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

    node = make_pr_reviewer_node(_FakeLLM([_CLEAN_REVIEW_JSON]), _BrokenRegistry())  # type: ignore[arg-type]
    command = await node(_make_state())

    assert command.goto == "supervisor"
    errors = command.update.get("errors", [])
    assert len(errors) == 1
    assert errors[0].code == "AGENT_ERROR"
    assert errors[0].agent == "pr_reviewer"
