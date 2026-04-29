"""Unit tests for the Code Search specialist agent.

Covers ranking determinism with fixed embeddings, hybrid deduplication,
and all integration paths (lexical-only, semantic-only, hybrid, empty results).
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from devhub.domain.agent_state import AgentState
from devhub.domain.agents.code_searcher import (
    _SCORE_BOOST,
    _extract_query,
    _extract_repo,
    _github_score,
    _merge_hits,
    _parse_github_hits,
    make_code_searcher_node,
)
from devhub.domain.models import CodeSearchHit
from devhub.domain.ports import IMCPRegistry, IVectorStore

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
        raise NotImplementedError

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


class _FakeVectorStore:
    """Returns pre-seeded hits regardless of query — deterministic for tests."""

    def __init__(self, hits: list[CodeSearchHit]) -> None:
        self._hits = hits

    async def search(self, query: str, *, k: int = 10) -> list[CodeSearchHit]:  # noqa: ARG002
        return self._hits[:k]


assert isinstance(_FakeVectorStore([]), IVectorStore)


class _FakeLLM:
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

_GITHUB_RESPONSE = json.dumps(
    {
        "total_count": 2,
        "items": [
            {
                "path": "src/auth/jwt.py",
                "repository": {"full_name": "myorg/myrepo"},
                "text_matches": [{"fragment": "def parse_jwt(token: str) -> dict:"}],
            },
            {
                "path": "tests/test_auth.py",
                "repository": {"full_name": "myorg/myrepo"},
                "text_matches": [{"fragment": "result = parse_jwt(token)"}],
            },
        ],
    }
)
_GITHUB_EMPTY = json.dumps({"total_count": 0, "items": []})
_GITHUB_ERROR = "[error calling search_code: 422 Unprocessable Entity]"

_VECTOR_HITS_FIXED = [
    CodeSearchHit(
        repo="myorg/myrepo",
        path="src/auth/jwt.py",
        start_line=42,
        end_line=55,
        snippet="def parse_jwt(token: str) -> dict:",
        score=0.92,
        source="vector",
    ),
    CodeSearchHit(
        repo="myorg/myrepo",
        path="src/auth/session.py",
        start_line=10,
        end_line=20,
        snippet="def create_session(user_id: str) -> str:",
        score=0.75,
        source="vector",
    ),
]

_SYNTHESIS_ANSWER = "The `parse_jwt` function is defined in `src/auth/jwt.py:42`."


def _make_state(content: str) -> AgentState:
    return AgentState(
        messages=[HumanMessage(content=content)],
        current_agent="code_searcher",
        plan=[],
        artifacts={},
        errors=[],
        interrupt_request=None,
    )


# ── Pure helper tests ─────────────────────────────────────────────────────────


def test_extract_repo_from_github_url() -> None:
    msgs = [HumanMessage(content=f"Search {_REPO_URL} for parse_jwt")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_from_bare_notation() -> None:
    msgs = [HumanMessage(content="Where is parse_jwt in myorg/myrepo?")]
    assert _extract_repo(msgs) == ("myorg", "myrepo")


def test_extract_repo_returns_none_when_absent() -> None:
    assert _extract_repo([HumanMessage(content="Where is parse_jwt?")]) is None


def test_extract_query_from_backtick_quoted() -> None:
    msgs = [HumanMessage(content="Where do we call `authenticate_user` in myorg/myrepo?")]
    query = _extract_query(msgs, ("myorg", "myrepo"))
    assert query == "authenticate_user"


def test_extract_query_from_double_quoted() -> None:
    msgs = [HumanMessage(content='Search myorg/myrepo for "payment retry logic"')]
    query = _extract_query(msgs, ("myorg", "myrepo"))
    assert query == "payment retry logic"


def test_extract_query_strips_question_prefix() -> None:
    msgs = [HumanMessage(content="How does authentication work in myorg/myrepo?")]
    query = _extract_query(msgs, ("myorg", "myrepo"))
    assert "authentication" in query
    assert "how does" not in query.lower()


def test_extract_query_strips_repo_reference() -> None:
    msgs = [HumanMessage(content="Search myorg/myrepo for JWT validation")]
    query = _extract_query(msgs, ("myorg", "myrepo"))
    assert "myorg" not in query
    assert "myrepo" not in query
    assert "JWT" in query or "jwt" in query.lower()


def test_github_score_first_rank_is_highest() -> None:
    assert _github_score(0) > _github_score(1) > _github_score(2)


def test_github_score_rank_zero_is_one() -> None:
    assert _github_score(0) == pytest.approx(1.0)


def test_parse_github_hits_standard_response() -> None:
    hits = _parse_github_hits(_GITHUB_RESPONSE)
    assert len(hits) == 2
    assert hits[0].path == "src/auth/jwt.py"
    assert hits[0].repo == "myorg/myrepo"
    assert hits[0].source == "github"
    assert "parse_jwt" in hits[0].snippet


def test_parse_github_hits_empty_response() -> None:
    assert _parse_github_hits(_GITHUB_EMPTY) == []


def test_parse_github_hits_error_string() -> None:
    assert _parse_github_hits(_GITHUB_ERROR) == []


def test_parse_github_hits_assigns_descending_scores() -> None:
    hits = _parse_github_hits(_GITHUB_RESPONSE)
    assert hits[0].score > hits[1].score


def test_merge_hits_deduplicates_same_file() -> None:
    """Same (repo, path) from both sources → single merged hit with boosted score."""
    gh = [
        CodeSearchHit(
            repo="r",
            path="auth.py",
            start_line=1,
            end_line=1,
            snippet="",
            score=0.8,
            source="github",
        )
    ]
    vec = [
        CodeSearchHit(
            repo="r",
            path="auth.py",
            start_line=10,
            end_line=20,
            snippet="def authenticate",
            score=0.85,
            source="vector",
        )
    ]
    result = _merge_hits(gh, vec, max_results=10)
    assert len(result) == 1
    assert result[0].source == "merged"
    assert result[0].score == pytest.approx(min(1.0, 0.85 + _SCORE_BOOST))
    assert result[0].start_line == 10  # vector's more precise lines preferred


def test_merge_hits_sorts_by_score_descending() -> None:
    """Ranking is deterministic given fixed scores."""
    gh = [
        CodeSearchHit(
            repo="r", path="a.py", start_line=1, end_line=1, snippet="", score=0.9, source="github"
        ),
        CodeSearchHit(
            repo="r", path="b.py", start_line=1, end_line=1, snippet="", score=0.6, source="github"
        ),
    ]
    vec = [
        CodeSearchHit(
            repo="r",
            path="c.py",
            start_line=1,
            end_line=5,
            snippet="c",
            score=0.75,
            source="vector",
        ),
    ]
    result = _merge_hits(gh, vec, max_results=10)
    assert result[0].path == "a.py"
    assert result[1].path == "c.py"
    assert result[2].path == "b.py"


def test_merge_hits_caps_at_max_results() -> None:
    hits = [
        CodeSearchHit(
            repo="r",
            path=f"{i}.py",
            start_line=1,
            end_line=1,
            snippet="",
            score=float(i) / 20,
            source="github",
        )
        for i in range(15)
    ]
    result = _merge_hits(hits, [], max_results=5)
    assert len(result) == 5


def test_merge_ranking_is_deterministic_with_fixed_inputs() -> None:
    """Same inputs always produce same ranking — required by story AC."""
    gh = _parse_github_hits(_GITHUB_RESPONSE)
    vec = list(_VECTOR_HITS_FIXED)
    result_a = _merge_hits(gh, vec, max_results=10)
    result_b = _merge_hits(gh, vec, max_results=10)
    assert [h.path for h in result_a] == [h.path for h in result_b]
    assert [h.score for h in result_a] == [h.score for h in result_b]


# ── Integration tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lexical_search_returns_hits() -> None:
    """GitHub-only results (no vector store)."""
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_RESPONSE)])
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry, vector_store=None)

    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))
    assert command.goto == "supervisor"
    artifacts = command.update.get("artifacts", {})
    assert "code_search" in artifacts
    hits = artifacts["code_search"]["hits"]
    assert len(hits) >= 1
    assert any(h["path"] == "src/auth/jwt.py" for h in hits)


@pytest.mark.asyncio
async def test_semantic_search_returns_hits() -> None:
    """Vector-only results (GitHub tool unavailable)."""
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_EMPTY)])
    vector_store = _FakeVectorStore(_VECTOR_HITS_FIXED)
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry, vector_store)

    command = await node(_make_state("How does session management work in myorg/myrepo?"))
    artifacts = command.update.get("artifacts", {})
    hits = artifacts["code_search"]["hits"]
    assert any(h["source"] == "vector" for h in hits)


@pytest.mark.asyncio
async def test_hybrid_search_deduplicates_overlapping_file() -> None:
    """jwt.py appears in both GitHub and vector → single merged hit, boosted score."""
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_RESPONSE)])
    vector_store = _FakeVectorStore(_VECTOR_HITS_FIXED)
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry, vector_store)

    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))
    hits = command.update["artifacts"]["code_search"]["hits"]

    jwt_hits = [h for h in hits if h["path"] == "src/auth/jwt.py"]
    assert len(jwt_hits) == 1
    assert jwt_hits[0]["source"] == "merged"
    assert jwt_hits[0]["score"] > 0.92


@pytest.mark.asyncio
async def test_search_result_stored_in_artifacts() -> None:
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_RESPONSE)])
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry)

    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))
    artifacts = command.update.get("artifacts", {})
    assert "code_search" in artifacts
    result = artifacts["code_search"]
    assert "query" in result
    assert "hits" in result
    assert result["total"] == len(result["hits"])


@pytest.mark.asyncio
async def test_llm_synthesis_appears_in_reply() -> None:
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_RESPONSE)])
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry)

    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))
    reply = command.update["messages"][0].content
    assert "parse_jwt" in reply or "jwt.py" in reply.lower()


@pytest.mark.asyncio
async def test_empty_results_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_EMPTY)])
    vector_store = _FakeVectorStore([])
    llm = _FakeLLM([])
    node = make_code_searcher_node(llm, registry, vector_store)

    command = await node(_make_state(f"Where is `nonexistent_symbol` in {_REPO_URL}?"))
    reply = command.update["messages"][0].content
    assert "no results" in reply.lower() or "not found" in reply.lower()


@pytest.mark.asyncio
async def test_missing_query_returns_helpful_message() -> None:
    registry = _FakeMCPRegistry([])
    llm = _FakeLLM([])
    node = make_code_searcher_node(llm, registry)

    command = await node(_make_state("  "))  # blank message
    assert command.goto == "supervisor"
    reply = command.update["messages"][0].content
    assert "query" in reply.lower() or "search" in reply.lower()


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

    node = make_code_searcher_node(_FakeLLM([]), _BrokenRegistry())  # type: ignore[arg-type]
    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))

    assert command.goto == "supervisor"
    errors = command.update.get("errors", [])
    assert len(errors) == 1
    assert errors[0].code == "AGENT_ERROR"
    assert errors[0].agent == "code_searcher"


@pytest.mark.asyncio
async def test_hits_include_required_fields() -> None:
    """All result fields (repo, path, start_line, end_line, snippet, score) are present."""
    registry = _FakeMCPRegistry([_FakeTool("search_code", _GITHUB_RESPONSE)])
    llm = _FakeLLM([_SYNTHESIS_ANSWER])
    node = make_code_searcher_node(llm, registry)

    command = await node(_make_state(f"Where is `parse_jwt` in {_REPO_URL}?"))
    hits = command.update["artifacts"]["code_search"]["hits"]
    for hit in hits:
        assert "repo" in hit
        assert "path" in hit
        assert "start_line" in hit
        assert "end_line" in hit
        assert "snippet" in hit
        assert "score" in hit
