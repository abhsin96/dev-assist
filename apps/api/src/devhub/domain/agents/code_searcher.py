"""Code Search specialist agent — hybrid lexical + semantic retrieval.

Flow:
1. Extract the search query and optional repo filter from the user message.
2. Run GitHub ``search_code`` (lexical / exact-symbol match) via MCP.
3. Run vector similarity search over embedded code chunks via ``IVectorStore``.
4. Merge results: deduplicate by (repo, path), boost score for hits that appear
   in both sources, sort descending, cap at ``_MAX_RESULTS``.
5. Synthesise a brief natural-language answer via the LLM citing the top hits.
6. Return result — no HITL needed (read-only operation).
"""

from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from devhub.domain.agent_state import AgentErrorRecord, AgentState
from devhub.domain.agents.base import AgentConfig
from devhub.domain.models import CodeSearchHit, CodeSearchResult
from devhub.domain.ports import ILLMPort, IMCPRegistry, IVectorStore

config = AgentConfig(
    agent_id="code_searcher",
    allowed_servers=frozenset({"github", "filesystem"}),
)

_MAX_RESULTS = 10
_GITHUB_MAX = 10
_VECTOR_MAX = 10
_SCORE_BOOST = 0.1  # added when a result appears in both sources

_SEARCH_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "code_searcher.md").read_text()

_GITHUB_URL_RE = re.compile(
    r"github\.com/([A-Za-z0-9][A-Za-z0-9_.-]*)/([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
_BARE_REPO_RE = re.compile(
    r"(?:^|[ \t(])([A-Za-z0-9][A-Za-z0-9_-]{1,})/([A-Za-z0-9][A-Za-z0-9_-]{1,})(?![/\w])"
)
# Quoted or backtick-delimited symbols get priority as the query.
_QUOTED_QUERY_RE = re.compile(r'["`]([^"`\n]{1,200})["`]')
# Common question prefixes to strip.
_QUESTION_PREFIX_RE = re.compile(
    r"^(?:search(?:\s+\S+)?\s+for\s+"
    r"|find\s+(?:where\s+)?"
    r"|where\s+(?:is\s+|do\s+we\s+(?:call\s+|use\s+)|are\s+)?"
    r"|how\s+does?\s+"
    r"|what\s+is\s+"
    r"|show\s+me\s+)",
    re.IGNORECASE,
)
# Trailing location phrases to strip.
_LOCATION_SUFFIX_RE = re.compile(
    r"\s+(?:in\s+(?:this\s+repo|the\s+codebase|our\s+code|this\s+project)"
    r"|defined|implemented|called|used)\s*$",
    re.IGNORECASE,
)


# ── Input extraction ──────────────────────────────────────────────────────────


def _extract_repo(messages: list[Any]) -> tuple[str, str] | None:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        m = _GITHUB_URL_RE.search(content)
        if m:
            return m.group(1), m.group(2).rstrip("/")
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        m = _BARE_REPO_RE.search(content)
        if m:
            return m.group(1), m.group(2)
    return None


def _extract_query(messages: list[Any], repo_coords: tuple[str, str] | None) -> str:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue

        # Quoted / backtick symbol takes priority.
        m = _QUOTED_QUERY_RE.search(content)
        if m:
            return m.group(1).strip()

        text = content
        # Strip repo reference.
        if repo_coords:
            owner, repo = repo_coords
            for pat in (f"https://github.com/{owner}/{repo}", f"{owner}/{repo}"):
                text = text.replace(pat, "").strip()
        # Strip common question prefix.
        text = _QUESTION_PREFIX_RE.sub("", text).strip()
        # Strip trailing location phrase.
        text = _LOCATION_SUFFIX_RE.sub("", text).strip()
        text = text.rstrip("?!.,").strip()
        if text:
            return text
    return ""


# ── GitHub hit parsing ────────────────────────────────────────────────────────


def _github_score(rank: int) -> float:
    return 1.0 / (1.0 + rank)


def _parse_github_hits(raw: str) -> list[CodeSearchHit]:
    if not raw or raw.startswith("["):
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return []
        items = data.get("items", [])
        if not isinstance(items, list):
            return []
        hits: list[CodeSearchHit] = []
        for rank, item in enumerate(items[:_GITHUB_MAX]):
            if not isinstance(item, dict):
                continue
            repo = ""
            repo_info = item.get("repository", {})
            if isinstance(repo_info, dict):
                repo = str(repo_info.get("full_name", ""))
            path = str(item.get("path", ""))
            snippet = ""
            matches = item.get("text_matches", [])
            if isinstance(matches, list) and matches:
                first = matches[0]
                if isinstance(first, dict):
                    snippet = str(first.get("fragment", ""))[:500]
            if not repo or not path:
                continue
            hits.append(
                CodeSearchHit(
                    repo=repo,
                    path=path,
                    start_line=1,
                    end_line=1,
                    snippet=snippet,
                    score=_github_score(rank),
                    source="github",
                )
            )
        return hits
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


# ── Merge ─────────────────────────────────────────────────────────────────────


def _merge_hits(
    github_hits: list[CodeSearchHit],
    vector_hits: list[CodeSearchHit],
    max_results: int = _MAX_RESULTS,
) -> list[CodeSearchHit]:
    """Deduplicate by (repo, path), boost score for hits in both sources, rank descending."""
    merged: dict[tuple[str, str], CodeSearchHit] = {}

    for hit in github_hits:
        key = (hit.repo, hit.path)
        merged[key] = hit

    for hit in vector_hits:
        key = (hit.repo, hit.path)
        if key in merged:
            existing = merged[key]
            boosted = min(1.0, max(existing.score, hit.score) + _SCORE_BOOST)
            # Prefer vector hit's line numbers (more precise); use richer snippet.
            merged[key] = CodeSearchHit(
                repo=existing.repo,
                path=existing.path,
                start_line=hit.start_line,
                end_line=hit.end_line,
                snippet=hit.snippet or existing.snippet,
                score=boosted,
                source="merged",
            )
        else:
            merged[key] = hit

    ranked = sorted(merged.values(), key=lambda h: h.score, reverse=True)
    return ranked[:max_results]


# ── Synthesis ─────────────────────────────────────────────────────────────────


def _synthesis_context(query: str, hits: list[CodeSearchHit]) -> str:
    lines = [f"Developer question: {query}\n", "Retrieved results:"]
    for i, hit in enumerate(hits[:5], 1):
        lines.append(f"\n{i}. {hit.repo}/{hit.path}:{hit.start_line}")
        if hit.snippet:
            lines.append(f"   ```\n   {hit.snippet[:300]}\n   ```")
    return "\n".join(lines)


# ── Tool calling ──────────────────────────────────────────────────────────────


async def _call_tool(tools: list[BaseTool], tool_name: str, args: dict[str, Any]) -> str:
    tool = next((t for t in tools if t.name == tool_name), None)
    if tool is None:
        return f"[tool {tool_name!r} not available]"
    try:
        result = await tool.arun(args)
        return str(result)
    except Exception as exc:
        return f"[error calling {tool_name}: {exc}]"


# ── Node factory ──────────────────────────────────────────────────────────────


def make_code_searcher_node(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None,
    vector_store: IVectorStore | None = None,
) -> Callable[[AgentState], Any]:
    """Return a LangGraph node for the code searcher.

    ``vector_store`` is the semantic search backend.  Pass ``None`` to fall
    back to lexical-only search (GitHub MCP).
    """

    async def code_searcher(state: AgentState) -> Command[str]:
        try:
            tools: list[BaseTool] = []
            if mcp_registry is not None:
                tools = await mcp_registry.tools_for("code_searcher")

            repo_coords = _extract_repo(list(state["messages"]))
            query = _extract_query(list(state["messages"]), repo_coords)

            if not query:
                reply = AIMessage(
                    content=(
                        "I couldn't identify a search query in your message. "
                        "Try something like: "
                        '"Where is `authenticate_user` called?" or '
                        '"How does the payment retry work?"'
                    )
                )
                return Command(
                    goto="supervisor",
                    update={"messages": [reply], "current_agent": "supervisor"},
                )

            # Build GitHub search query — append repo filter when available.
            github_q = query
            if repo_coords:
                owner, repo = repo_coords
                github_q = f"{query} repo:{owner}/{repo}"

            # Lexical search via GitHub MCP.
            github_raw = await _call_tool(
                tools,
                "search_code",
                {"q": github_q, "per_page": _GITHUB_MAX},
            )
            github_hits = _parse_github_hits(github_raw)

            # Semantic search via vector store.
            vector_hits: list[CodeSearchHit] = []
            if vector_store is not None:
                vector_hits = await vector_store.search(query, k=_VECTOR_MAX)

            merged = _merge_hits(github_hits, vector_hits, max_results=_MAX_RESULTS)

            if not merged:
                reply = AIMessage(
                    content=(
                        f'No results found for "{query}". '
                        "Try a more specific symbol name or a different phrasing."
                    )
                )
                return Command(
                    goto="supervisor",
                    update={"messages": [reply], "current_agent": "supervisor"},
                )

            # LLM synthesis — natural language answer with citations.
            synthesis_input = _synthesis_context(query, merged)
            response = await llm.chat(
                [HumanMessage(content=synthesis_input)],
                system=_SEARCH_PROMPT,
            )
            answer = str(response.content)

            result = CodeSearchResult(query=query, hits=merged, total=len(merged))

            artifacts: dict[str, Any] = dict(state.get("artifacts") or {})
            artifacts["code_search"] = result.model_dump()

            return Command(
                goto="supervisor",
                update={
                    "messages": [AIMessage(content=answer)],
                    "current_agent": "supervisor",
                    "artifacts": artifacts,
                },
            )

        except Exception as exc:
            error = AgentErrorRecord(
                code="AGENT_ERROR",
                message=str(exc),
                agent="code_searcher",
                retryable=False,
            )
            return Command(
                goto="supervisor",
                update={"errors": [error], "current_agent": "supervisor"},
            )

    return code_searcher
