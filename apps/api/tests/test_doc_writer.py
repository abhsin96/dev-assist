"""Unit tests for the Doc Writer specialist agent.

All tests use a fake MCP registry and a fake LLM — no real network calls.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from devhub.domain.agent_state import AgentState
from devhub.domain.agents.doc_writer import (
    _decode_file_content,
    _doc_mode_for_path,
    _extract_repo,
    _extract_target_path,
    _unified_diff,
    make_doc_writer_node,
)
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


# ── Fixtures ──────────────────────────────────────────────────────────────────

_REPO_URL = "https://github.com/myorg/myrepo"

_REPO_META = json.dumps(
    {
        "full_name": "myorg/myrepo",
        "description": "A sample Python utility library.",
        "language": "Python",
        "topics": ["python", "utilities"],
        "default_branch": "main",
    }
)
_FILE_TREE = json.dumps(
    [
        {"name": "src", "type": "dir"},
        {"name": "tests", "type": "dir"},
        {"name": "pyproject.toml", "type": "file"},
    ]
)
_NOT_FOUND = "[error calling get_file_contents: 404 Not Found]"

_EXISTING_README = "# My Repo\n\nOld description.\n"
_UPDATED_README = (
    "# My Repo\n\n"
    "## Overview\n\nA Python utility library with lots of helpers.\n\n"
    "## Installation\n\n```bash\npip install myrepo\n```\n"
)

_SOURCE_FILE = "def add(a, b):\n    return a + b\n"
_SOURCE_WITH_DOCSTRINGS = (
    '"""Utility math functions."""\n\n'
    "def add(a, b):\n"
    '    """Return the sum of a and b."""\n'
    "    return a + b\n"
)


def _b64_wrap(text: str) -> str:
    encoded = base64.b64encode(text.encode()).decode()
    return json.dumps({"content": encoded, "encoding": "base64", "sha": "deadbeef"})


def _make_state(content: str = f"Write docs for {_REPO_URL}") -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=content)],
        current_agent="doc_writer",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )


def _readme_tools(file_raw: str = _NOT_FOUND) -> list[BaseTool]:
    return [
        _FakeTool("get_repository", _REPO_META),
        _FakeTool("get_file_contents", file_raw),
        _FakeTool("list_directory_contents", _FILE_TREE),
    ]


def _docstring_tools(source_raw: str) -> list[BaseTool]:
    return [
        _FakeTool("get_repository", _REPO_META),
        _FakeTool("get_file_contents", source_raw),
        _FakeTool("list_directory_contents", _FILE_TREE),
    ]


# ── Pure helper tests ─────────────────────────────────────────────────────────


def test_extract_repo_from_github_url() -> None:
    msgs = [HumanMessage(content=f"Write docs for {_REPO_URL}")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_from_bare_notation() -> None:
    msgs = [HumanMessage(content="Write docs for myorg/myrepo")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_returns_none_when_missing() -> None:
    assert _extract_repo([HumanMessage(content="Write some docs")]) is None


def test_extract_target_path_explicit_md() -> None:
    msgs = [HumanMessage(content="Update README.md in myorg/myrepo")]
    assert _extract_target_path(msgs) == "README.md"


def test_extract_target_path_source_file() -> None:
    msgs = [HumanMessage(content="Add docstrings to src/utils.py in myorg/myrepo")]
    assert _extract_target_path(msgs) == "src/utils.py"


def test_extract_target_path_defaults_to_readme() -> None:
    msgs = [HumanMessage(content="Write docs for myorg/myrepo")]
    assert _extract_target_path(msgs) == "README.md"


def test_doc_mode_for_readme() -> None:
    assert _doc_mode_for_path("README.md") == "greenfield"


def test_doc_mode_for_python_file() -> None:
    assert _doc_mode_for_path("src/utils.py") == "docstring"


def test_doc_mode_for_ts_file() -> None:
    assert _doc_mode_for_path("src/index.ts") == "docstring"


def test_decode_file_content_from_base64_json() -> None:
    raw = _b64_wrap("Hello, world!\n")
    assert _decode_file_content(raw) == "Hello, world!\n"


def test_decode_file_content_returns_none_on_error_string() -> None:
    assert _decode_file_content(_NOT_FOUND) is None


def test_decode_file_content_returns_none_on_empty() -> None:
    assert _decode_file_content("") is None


def test_unified_diff_shows_changes() -> None:
    diff = _unified_diff("old line\n", "new line\n", "README.md")
    assert "-old line" in diff
    assert "+new line" in diff


def test_unified_diff_empty_for_identical_content() -> None:
    assert _unified_diff("same\n", "same\n", "README.md") == ""


# ── Integration tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_greenfield_readme_generates_draft() -> None:
    """No existing README → mode=greenfield, diff=None, HITL created."""
    registry = _FakeMCPRegistry(_readme_tools(_NOT_FOUND))
    llm = _FakeLLM([_UPDATED_README])
    node = make_doc_writer_node(llm, registry)

    command = await node(_make_state())
    assert command.goto == "supervisor"
    body = json.loads(command.update["messages"][0].content)
    assert body["mode"] == "greenfield"
    assert body["diff"] is None
    assert len(body["draft"]) > 0
    assert body["owner"] == "myorg"
    assert body["target_path"] == "README.md"


@pytest.mark.asyncio
async def test_greenfield_creates_hitl_for_pr() -> None:
    registry = _FakeMCPRegistry(_readme_tools(_NOT_FOUND))
    llm = _FakeLLM([_UPDATED_README])
    node = make_doc_writer_node(llm, registry)

    command = await node(_make_state())
    hitl = command.update.get("interrupt_request")
    assert hitl is not None
    assert hitl.tool_name == "create_pull_request_with_file"
    assert hitl.tool_args["owner"] == "myorg"
    assert hitl.tool_args["path"] == "README.md"
    assert "devhub/docs-" in hitl.tool_args["branch"]


@pytest.mark.asyncio
async def test_update_readme_produces_diff() -> None:
    """Existing README found → mode=update, diff is a non-empty unified diff."""
    registry = _FakeMCPRegistry(_readme_tools(_b64_wrap(_EXISTING_README)))
    llm = _FakeLLM([_UPDATED_README])
    node = make_doc_writer_node(llm, registry)

    command = await node(_make_state())
    body = json.loads(command.update["messages"][0].content)
    assert body["mode"] == "update"
    assert body["diff"] is not None
    assert "-Old description." in body["diff"]
    assert "+A Python utility library" in body["diff"]


@pytest.mark.asyncio
async def test_update_no_changes_no_hitl() -> None:
    """If the LLM returns identical content, diff is empty and no HITL is raised."""
    registry = _FakeMCPRegistry(_readme_tools(_b64_wrap(_EXISTING_README)))
    llm = _FakeLLM([_EXISTING_README])  # LLM returns same content
    node = make_doc_writer_node(llm, registry)

    command = await node(_make_state())
    body = json.loads(command.update["messages"][0].content)
    assert body["mode"] == "update"
    assert body["diff"] is None
    assert command.update.get("interrupt_request") is None


@pytest.mark.asyncio
async def test_docstring_sweep_produces_diff() -> None:
    """Source file input → mode=docstring, diff shows added docstrings."""
    registry = _FakeMCPRegistry(_docstring_tools(_b64_wrap(_SOURCE_FILE)))
    llm = _FakeLLM([_SOURCE_WITH_DOCSTRINGS])
    node = make_doc_writer_node(
        llm,
        registry,
    )

    state = _make_state(f"Add docstrings to src/utils.py in {_REPO_URL}")
    command = await node(state)
    body = json.loads(command.update["messages"][0].content)
    assert body["mode"] == "docstring"
    assert body["target_path"] == "src/utils.py"
    assert body["diff"] is not None
    assert "Utility math functions" in body["diff"]


@pytest.mark.asyncio
async def test_docstring_sweep_creates_hitl() -> None:
    registry = _FakeMCPRegistry(_docstring_tools(_b64_wrap(_SOURCE_FILE)))
    llm = _FakeLLM([_SOURCE_WITH_DOCSTRINGS])
    node = make_doc_writer_node(llm, registry)

    state = _make_state(f"Add docstrings to src/utils.py in {_REPO_URL}")
    command = await node(state)
    hitl = command.update.get("interrupt_request")
    assert hitl is not None
    assert hitl.tool_args["path"] == "src/utils.py"


@pytest.mark.asyncio
async def test_docstring_file_not_found_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry(_docstring_tools(_NOT_FOUND))
    llm = _FakeLLM([])
    node = make_doc_writer_node(llm, registry)

    state = _make_state(f"Add docstrings to src/utils.py in {_REPO_URL}")
    command = await node(state)
    reply = command.update["messages"][0].content
    assert "src/utils.py" in reply or "not found" in reply.lower() or "could not" in reply.lower()


@pytest.mark.asyncio
async def test_missing_repo_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry([])
    llm = _FakeLLM([])
    node = make_doc_writer_node(llm, registry)

    command = await node(
        AgentState(
            messages=[HumanMessage(content="Write some docs please")],
            current_agent="doc_writer",
            plan=[],
            artifacts={},
            errors=[],
            interrupt_request=None,
        )
    )
    assert command.goto == "supervisor"
    reply = command.update["messages"][0].content
    assert "github" in reply.lower() or "repository" in reply.lower()


@pytest.mark.asyncio
async def test_result_stored_in_artifacts() -> None:
    registry = _FakeMCPRegistry(_readme_tools(_NOT_FOUND))
    llm = _FakeLLM([_UPDATED_README])
    node = make_doc_writer_node(llm, registry)

    command = await node(_make_state())
    artifacts = command.update.get("artifacts", {})
    assert "doc_write" in artifacts
    doc = artifacts["doc_write"]
    assert doc["owner"] == "myorg"
    assert doc["mode"] == "greenfield"
    assert "draft" in doc


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

    node = make_doc_writer_node(_FakeLLM([]), _BrokenRegistry())  # type: ignore[arg-type]
    command = await node(_make_state())

    assert command.goto == "supervisor"
    errors = command.update.get("errors", [])
    assert len(errors) == 1
    assert errors[0].code == "AGENT_ERROR"
    assert errors[0].agent == "doc_writer"
