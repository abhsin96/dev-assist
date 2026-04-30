"""PR Reviewer specialist agent.

Fetches a PR's diff and files via the GitHub MCP server, runs a structured
LLM review, then runs a reflection pass to validate blocking items.  Posting
the review comment requires explicit HITL approval — this node never auto-posts.
"""

from __future__ import annotations

import json
import pathlib
import re
import uuid
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command

from devhub.domain.agent_state import AgentErrorRecord, AgentState, HITLRequest
from devhub.domain.agents.base import AgentConfig
from devhub.domain.models import PRReview
from devhub.domain.ports import ILLMPort, IMCPRegistry

config = AgentConfig(
    agent_id="pr_reviewer",
    allowed_servers=frozenset({"github"}),
)

_PR_URL_RE = re.compile(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)")
_MAX_DIFF_CHARS = 40_000

_REVIEW_PROMPT = (pathlib.Path(__file__).parent.parent / "prompts" / "pr_reviewer.md").read_text()

_REFLECTION_PROMPT = (
    pathlib.Path(__file__).parent.parent / "prompts" / "pr_reviewer_reflection.md"
).read_text()

# Path fragments that indicate security-sensitive files (case-insensitive substring match).
_SECURITY_SENSITIVE_FRAGMENTS: frozenset[str] = frozenset(
    {
        "auth",
        "security",
        "crypto",
        "jwt",
        "oauth",
        "permission",
        "token",
        "secret",
        "credential",
        ".env",
        ".github/workflows",
        "dockerfile",
        "docker-compose",
    }
)


# ── URL / path helpers ────────────────────────────────────────────────────────


def _extract_pr_url(messages: list[Any]) -> tuple[str, str, str] | None:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if isinstance(content, str):
            m = _PR_URL_RE.search(content)
            if m:
                return m.group(1), m.group(2), m.group(3)
    return None


def _is_security_sensitive(path: str) -> bool:
    p = path.lower()
    return any(frag in p for frag in _SECURITY_SENSITIVE_FRAGMENTS)


def _find_sensitive_paths(files_raw: str) -> list[str]:
    try:
        files = json.loads(files_raw)
        if isinstance(files, list):
            return [
                entry.get("filename", "") if isinstance(entry, dict) else str(entry)
                for entry in files
                if _is_security_sensitive(
                    entry.get("filename", "") if isinstance(entry, dict) else str(entry)
                )
            ]
    except (json.JSONDecodeError, AttributeError):
        pass
    return []


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


# ── LLM response parsing ──────────────────────────────────────────────────────


def _parse_review(content: str) -> PRReview:
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            return PRReview(
                summary=str(data.get("summary", "")),
                blocking=list(data.get("blocking", [])),
                non_blocking=list(data.get("non_blocking", [])),
                nits=list(data.get("nits", [])),
                suggested_comment=str(data.get("suggested_comment", "")),
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return PRReview(
        summary=content,
        blocking=[],
        non_blocking=[],
        nits=[],
        suggested_comment="",
    )


def _apply_reflection(review: PRReview, reflection_content: str) -> PRReview:
    try:
        start = reflection_content.find("{")
        end = reflection_content.rfind("}") + 1
        if start != -1 and end > start:
            data = json.loads(reflection_content[start:end])
            final_blocking = list(data.get("validated_blocking", review.blocking))
            final_blocking += list(data.get("additional_blocking", []))
            return PRReview(
                summary=review.summary,
                blocking=final_blocking,
                non_blocking=review.non_blocking,
                nits=review.nits,
                suggested_comment=review.suggested_comment,
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return review


# ── Formatting ───────────────────────────────────────────────────────────────


def _format_review_markdown(review: PRReview, owner: str, repo: str, pr_number: str) -> str:
    lines: list[str] = []
    lines.append(
        f"## PR Review: [{owner}/{repo}#{pr_number}](https://github.com/{owner}/{repo}/pull/{pr_number})"
    )
    lines.append(f"\n{review.summary}")
    if review.blocking:
        lines.append("\n### 🚫 Blocking")
        lines.extend(f"- {item}" for item in review.blocking)
    if review.non_blocking:
        lines.append("\n### 💡 Suggestions")
        lines.extend(f"- {item}" for item in review.non_blocking)
    if review.nits:
        lines.append("\n### 🔍 Nits")
        lines.extend(f"- {item}" for item in review.nits)
    if not review.blocking and not review.non_blocking and not review.nits:
        lines.append("\n✅ No issues found.")
    return "\n".join(lines)


# ── Node factory ──────────────────────────────────────────────────────────────


def make_pr_reviewer_node(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None,
) -> Callable[[AgentState], Any]:
    """Return a LangGraph node function for the PR reviewer.

    ``mcp_registry`` is used to fetch GitHub tools at invocation time.
    Pass ``None`` to run without any MCP tools (tests / degraded mode).
    """

    async def pr_reviewer(state: AgentState) -> Command[str]:
        try:
            tools: list[BaseTool] = []
            if mcp_registry is not None:
                tools = await mcp_registry.tools_for("pr_reviewer")

            pr_coords = _extract_pr_url(list(state["messages"]))
            if not pr_coords:
                reply = AIMessage(
                    content=(
                        "I couldn't find a GitHub PR URL in your message. "
                        "Please provide one like https://github.com/owner/repo/pull/123"
                    )
                )
                return Command(
                    goto="supervisor",
                    update={"messages": [reply], "current_agent": "supervisor"},
                )

            owner, repo, pr_number = pr_coords

            diff = await _call_tool(
                tools,
                "get_pull_request_diff",
                {"owner": owner, "repo": repo, "pullNumber": int(pr_number)},
            )
            files_raw = await _call_tool(
                tools,
                "get_pull_request_files",
                {"owner": owner, "repo": repo, "pullNumber": int(pr_number)},
            )
            pr_meta = await _call_tool(
                tools,
                "get_pull_request",
                {"owner": owner, "repo": repo, "pullNumber": int(pr_number)},
            )

            sensitive_paths = _find_sensitive_paths(files_raw)
            truncated = len(diff) > _MAX_DIFF_CHARS
            if truncated:
                diff = diff[:_MAX_DIFF_CHARS]

            security_note = (
                (
                    f"\n\n**Security-sensitive paths changed:** {', '.join(sensitive_paths)}\n"
                    "Any change to these paths MUST be tagged as blocking unless provably safe."
                )
                if sensitive_paths
                else ""
            )
            truncation_note = (
                (
                    "\n\n**Note:** Diff was truncated to the first 40,000 characters. "
                    "Your review may be incomplete."
                )
                if truncated
                else ""
            )

            review_user_content = (
                f"PR: https://github.com/{owner}/{repo}/pull/{pr_number}\n\n"
                f"**Metadata:**\n{pr_meta}\n\n"
                f"**Files changed:**\n{files_raw}"
                f"{security_note}"
                f"\n\n**Diff:**\n{diff}"
                f"{truncation_note}"
            )

            review_response = await llm.chat(
                [HumanMessage(content=review_user_content)],
                system=_REVIEW_PROMPT,
            )
            review = _parse_review(str(review_response.content))

            if review.blocking:
                reflection_user_content = (
                    f"**Diff (for reference):**\n{diff}\n\n"
                    "**Blocking items to validate:**\n"
                    + "\n".join(f"- {item}" for item in review.blocking)
                )
                reflection_response = await llm.chat(
                    [HumanMessage(content=reflection_user_content)],
                    system=_REFLECTION_PROMPT,
                )
                review = _apply_reflection(review, str(reflection_response.content))

            artifacts: dict[str, Any] = dict(state.get("artifacts") or {})
            artifacts["pr_review"] = review.model_dump()

            reply = AIMessage(content=_format_review_markdown(review, owner, repo, pr_number))

            hitl_request: HITLRequest | None = None
            if review.suggested_comment:
                hitl_request = HITLRequest(
                    id=uuid.uuid4(),
                    prompt=(
                        f"Post the following review comment to "
                        f"{owner}/{repo}#{pr_number}?\n\n{review.suggested_comment}"
                    ),
                    tool_name="create_pull_request_review",
                    tool_args={
                        "owner": owner,
                        "repo": repo,
                        "pullNumber": int(pr_number),
                        "body": review.suggested_comment,
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
                agent="pr_reviewer",
                retryable=False,
            )
            return Command(
                goto="supervisor",
                update={"errors": [error], "current_agent": "supervisor"},
            )

    return pr_reviewer
