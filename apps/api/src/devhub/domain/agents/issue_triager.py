"""Issue Triager specialist agent.

Fetches open GitHub issues, detects duplicates via Jaccard similarity over
title + body preview, runs per-issue LLM triage, and gates all mutations
(label, assign, close-as-duplicate) behind a single batched HITL approval card.

Idempotency: triage results are cached by ``{owner}/{repo}/{number}/{updated_at}``
inside ``state["artifacts"]["triage_cache"]``.  Re-running on an unchanged issue
returns the cached result without an LLM call.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import uuid
from collections.abc import Callable
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from devhub.domain.agent_state import AgentErrorRecord, AgentState, HITLRequest
from devhub.domain.agents.base import AgentConfig
from devhub.domain.models import IssuePriority, IssueTriage, IssueTriageResult
from devhub.domain.ports import ILLMPort, IMCPRegistry

config = AgentConfig(
    agent_id="issue_triager",
    allowed_servers=frozenset({"github"}),
)

_MAX_ISSUES = 20
_SIMILARITY_THRESHOLD = 0.5
_BODY_PREVIEW_CHARS = 500
_VALID_PRIORITIES: frozenset[str] = frozenset({"P0", "P1", "P2", "P3"})

_GITHUB_URL_RE = re.compile(
    r"github\.com/([A-Za-z0-9][A-Za-z0-9_.-]*)/([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
_BARE_REPO_RE = re.compile(
    r"(?:^|[ \t(])([A-Za-z0-9][A-Za-z0-9_-]{1,})/([A-Za-z0-9][A-Za-z0-9_-]{1,})(?:[ \t),.]|$)"
)
_LABEL_RE = re.compile(r"\blabels?(?:ed)?[:\s]+([A-Za-z0-9_-]+)", re.IGNORECASE)

_TRIAGE_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "issue_triager.md").read_text()


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


def _extract_label_filter(messages: list[Any]) -> str | None:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            m = _LABEL_RE.search(content)
            if m:
                return m.group(1)
    return None


# ── Duplicate detection ───────────────────────────────────────────────────────


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    sa = set(re.findall(r"\w+", text_a.lower()))
    sb = set(re.findall(r"\w+", text_b.lower()))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _issue_text(issue: dict[str, Any]) -> str:
    title = str(issue.get("title", ""))
    body = str(issue.get("body") or "")
    return f"{title} {body[:_BODY_PREVIEW_CHARS]}"


def _detect_duplicate(issue: dict[str, Any], all_issues: list[dict[str, Any]]) -> int | None:
    """Return the number of the most-similar older issue above the threshold, or None."""
    number = int(issue.get("number", 0))
    text = _issue_text(issue)
    best_match: int | None = None
    best_score = _SIMILARITY_THRESHOLD
    for other in all_issues:
        other_number = int(other.get("number", 0))
        if other_number >= number:
            continue
        score = _jaccard_similarity(text, _issue_text(other))
        if score > best_score:
            best_score = score
            best_match = other_number
    return best_match


# ── Idempotency cache ─────────────────────────────────────────────────────────


def _cache_key(owner: str, repo: str, number: int, updated_at: str) -> str:
    raw = f"{owner}/{repo}/{number}/{updated_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── LLM response parsing ──────────────────────────────────────────────────────


def _parse_triage(content: str, issue_number: int, title: str) -> IssueTriage:
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            priority_raw = str(data.get("priority", "P3")).strip().upper()
            priority = cast(
                IssuePriority, priority_raw if priority_raw in _VALID_PRIORITIES else "P3"
            )
            return IssueTriage(
                issue_number=issue_number,
                title=title,
                priority=priority,
                labels=list(data.get("labels", [])),
                duplicate_of=data.get("duplicate_of"),
                suggested_assignee=data.get("suggested_assignee"),
                rationale=str(data.get("rationale", "")),
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return IssueTriage(
        issue_number=issue_number,
        title=title,
        priority="P3",
        labels=[],
        duplicate_of=None,
        suggested_assignee=None,
        rationale="Triage parsing failed — manual review required.",
    )


# ── HITL helpers ──────────────────────────────────────────────────────────────


def _has_mutations(triage: IssueTriage) -> bool:
    return bool(triage.labels or triage.duplicate_of is not None or triage.suggested_assignee)


def _build_hitl_prompt(owner: str, repo: str, triages: list[IssueTriage]) -> str:
    lines = [f"Apply the following triage mutations to {owner}/{repo}?\n"]
    for t in triages:
        lines.append(f"**Issue #{t.issue_number}: {t.title}**")
        if t.labels:
            lines.append(f"  Add labels: {', '.join(t.labels)}")
        if t.suggested_assignee:
            lines.append(f"  Assign to: @{t.suggested_assignee}")
        if t.duplicate_of is not None:
            lines.append(f"  Close as duplicate of #{t.duplicate_of}")
        lines.append(f"  Rationale: {t.rationale}")
        lines.append("")
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


def _parse_issues(raw: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


# ── Node factory ──────────────────────────────────────────────────────────────


def make_issue_triager_node(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None,
) -> Callable[[AgentState], Any]:
    """Return a LangGraph node for the issue triager.

    ``mcp_registry`` is used to fetch GitHub tools at invocation time.
    Pass ``None`` to run without MCP tools (tests / degraded mode).
    """

    async def issue_triager(state: AgentState) -> Command[str]:
        try:
            tools: list[BaseTool] = []
            if mcp_registry is not None:
                tools = await mcp_registry.tools_for("issue_triager")

            repo_coords = _extract_repo(list(state["messages"]))
            if not repo_coords:
                reply = AIMessage(
                    content=(
                        "I couldn't find a GitHub repository in your message. "
                        "Please provide one like https://github.com/owner/repo or owner/repo."
                    )
                )
                return Command(
                    goto="supervisor",
                    update={"messages": [reply], "current_agent": "supervisor"},
                )

            owner, repo = repo_coords
            label_filter = _extract_label_filter(list(state["messages"]))

            list_args: dict[str, Any] = {
                "owner": owner,
                "repo": repo,
                "state": "open",
                "per_page": _MAX_ISSUES,
            }
            if label_filter:
                list_args["labels"] = label_filter

            issues_raw = await _call_tool(tools, "list_issues", list_args)
            issues = _parse_issues(issues_raw)

            if not issues:
                reply = AIMessage(
                    content=(
                        f"No open issues found for {owner}/{repo} (or the tool is unavailable)."
                    )
                )
                return Command(
                    goto="supervisor",
                    update={"messages": [reply], "current_agent": "supervisor"},
                )

            artifacts: dict[str, Any] = dict(state.get("artifacts") or {})
            triage_cache: dict[str, dict[str, Any]] = dict(artifacts.get("triage_cache") or {})
            cache_hits = 0
            triages: list[IssueTriage] = []

            for issue in issues:
                number = int(issue.get("number", 0))
                title = str(issue.get("title", f"Issue #{number}"))
                updated_at = str(issue.get("updated_at", ""))
                key = _cache_key(owner, repo, number, updated_at)

                if key in triage_cache:
                    triages.append(IssueTriage(**triage_cache[key]))
                    cache_hits += 1
                    continue

                duplicate_of = _detect_duplicate(issue, issues)

                body = str(issue.get("body") or "")
                author = ""
                user = issue.get("user")
                if isinstance(user, dict):
                    author = str(user.get("login", ""))
                existing_labels = [
                    lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
                    for lbl in (issue.get("labels") or [])
                ]

                issue_content = (
                    f"Issue #{number}: {title}\n"
                    f"Author: {author}\n"
                    f"Created: {issue.get('created_at', '')}\n"
                    f"Existing labels: {', '.join(existing_labels) or 'none'}\n"
                    + (f"Potential duplicate of: #{duplicate_of}\n" if duplicate_of else "")
                    + f"\nBody:\n{body[:_BODY_PREVIEW_CHARS]}"
                )

                response = await llm.chat(
                    [HumanMessage(content=issue_content)],
                    system=_TRIAGE_PROMPT,
                )
                triage = _parse_triage(str(response.content), number, title)
                triage_cache[key] = triage.model_dump()
                triages.append(triage)

            artifacts["triage_cache"] = triage_cache

            result = IssueTriageResult(
                owner=owner,
                repo=repo,
                triaged=triages,
                cache_hits=cache_hits,
            )
            artifacts["issue_triage"] = result.model_dump()

            reply = AIMessage(content=result.model_dump_json(indent=2))

            hitl_request: HITLRequest | None = None
            mutation_triages = [t for t in triages if _has_mutations(t)]
            if mutation_triages:
                hitl_request = HITLRequest(
                    id=uuid.uuid4(),
                    prompt=_build_hitl_prompt(owner, repo, mutation_triages),
                    tool_name="apply_issue_triage_batch",
                    tool_args={
                        "owner": owner,
                        "repo": repo,
                        "mutations": [
                            {
                                "issue_number": t.issue_number,
                                "labels": t.labels,
                                "assignee": t.suggested_assignee,
                                "duplicate_of": t.duplicate_of,
                            }
                            for t in mutation_triages
                        ],
                    },
                )

            return Command(
                goto="supervisor",
                update={
                    "messages": [reply],
                    "current_agent": "supervisor",
                    "artifacts": artifacts,
                    "interrupt_request": hitl_request,
                },
            )

        except Exception as exc:
            error = AgentErrorRecord(
                code="AGENT_ERROR",
                message=str(exc),
                agent="issue_triager",
                retryable=False,
            )
            return Command(
                goto="supervisor",
                update={"errors": [error], "current_agent": "supervisor"},
            )

    return issue_triager
