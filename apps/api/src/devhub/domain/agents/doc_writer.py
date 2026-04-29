"""Doc Writer specialist agent.

Three modes, selected automatically from the target file path:

* **greenfield** — target file does not exist; generate from scratch.
* **update**     — target file exists; generate improved version and compute
                   a unified diff for the UI to render.
* **docstring**  — target is a source file (.py, .ts, …); sweep it for missing
                   module/function/class docstrings and produce the modified file
                   plus a unified diff.

Writing back to the repo (create a PR) is always gated by HITL — this node
never pushes directly.
"""

from __future__ import annotations

import base64
import difflib
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
from devhub.domain.models import DocMode, DocWriteResult
from devhub.domain.ports import ILLMPort, IMCPRegistry

config = AgentConfig(
    agent_id="doc_writer",
    allowed_servers=frozenset({"github", "filesystem"}),
)

_PROMPTS = pathlib.Path(__file__).parent.parent / "prompts"
_README_PROMPT = (_PROMPTS / "doc_writer.md").read_text()
_DOCSTRING_PROMPT = (_PROMPTS / "doc_writer_docstring.md").read_text()

_DOC_EXTENSIONS: frozenset[str] = frozenset({".md", ".rst", ".txt"})
_CODE_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs"}
)

_GITHUB_URL_RE = re.compile(
    r"github\.com/([A-Za-z0-9][A-Za-z0-9_.-]*)/([A-Za-z0-9][A-Za-z0-9_.-]*)"
)
_BARE_REPO_RE = re.compile(
    r"(?:^|[ \t(])([A-Za-z0-9][A-Za-z0-9_-]{1,})/([A-Za-z0-9][A-Za-z0-9_-]{1,})(?:[ \t),.]|$)"
)
_FILE_PATH_RE = re.compile(
    r"\b((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+"
    r"\.(?:md|rst|txt|py|ts|tsx|js|jsx|go|java|rb|rs))\b"
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


def _extract_target_path(messages: list[Any]) -> str:
    for msg in reversed(messages):
        content = getattr(msg, "content", "")
        if not isinstance(content, str):
            continue
        m = _FILE_PATH_RE.search(content)
        if m:
            return m.group(1)
    return "README.md"


def _doc_mode_for_path(path: str) -> DocMode:
    suffix = pathlib.Path(path).suffix.lower()
    if suffix in _CODE_EXTENSIONS:
        return "docstring"
    return "greenfield"  # may become "update" after existence check


# ── File content helpers ──────────────────────────────────────────────────────


def _decode_file_content(raw: str) -> str | None:
    """Return file text from a GitHub get_file_contents response, or None."""
    if not raw or raw.startswith("["):
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "content" in data:
            encoded = str(data["content"]).replace("\n", "")
            try:
                return base64.b64decode(encoded).decode("utf-8", errors="replace")
            except Exception:
                return str(data["content"])
    except (json.JSONDecodeError, TypeError):
        pass
    if not raw.startswith("["):
        return raw
    return None


def _summarize_file_tree(raw: str) -> str:
    """Convert a MCP directory listing to a readable string."""
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            lines: list[str] = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name", "")
                kind = entry.get("type", "")
                lines.append(f"{name}/" if kind == "dir" else name)
            return "\n".join(lines)
    except (json.JSONDecodeError, TypeError):
        pass
    return raw[:1000]


# ── Diff ─────────────────────────────────────────────────────────────────────


def _unified_diff(old: str, new: str, path: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}")
    )


# ── Prompt builders ───────────────────────────────────────────────────────────


def _readme_context(
    owner: str,
    repo: str,
    meta: str,
    file_tree: str,
    existing: str | None,
) -> str:
    parts = [
        f"Repository: {owner}/{repo}",
        f"Metadata:\n{meta}",
        f"Root files:\n{file_tree}",
    ]
    if existing:
        parts.append(f"Existing content:\n{existing}")
    return "\n\n".join(parts)


def _docstring_context(path: str, content: str) -> str:
    lang = pathlib.Path(path).suffix.lstrip(".")
    return f"File: {path}\nLanguage: {lang}\n\nContent:\n{content}"


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


def make_doc_writer_node(
    llm: ILLMPort,
    mcp_registry: IMCPRegistry | None,
) -> Callable[[AgentState], Any]:
    """Return a LangGraph node for the doc writer."""

    async def doc_writer(state: AgentState) -> Command[str]:
        try:
            tools: list[BaseTool] = []
            if mcp_registry is not None:
                tools = await mcp_registry.tools_for("doc_writer")

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
            target_path = _extract_target_path(list(state["messages"]))
            base_mode = _doc_mode_for_path(target_path)

            # Always fetch repo metadata for context
            meta_raw = await _call_tool(tools, "get_repository", {"owner": owner, "repo": repo})

            # Try to read the target file
            file_raw = await _call_tool(
                tools,
                "get_file_contents",
                {"owner": owner, "repo": repo, "path": target_path},
            )
            existing_content = _decode_file_content(file_raw)

            if base_mode == "docstring":
                if existing_content is None:
                    reply = AIMessage(
                        content=(
                            f"Could not read `{target_path}` from {owner}/{repo}. "
                            "Please check the path and try again."
                        )
                    )
                    return Command(
                        goto="supervisor",
                        update={"messages": [reply], "current_agent": "supervisor"},
                    )

                prompt_input = _docstring_context(target_path, existing_content)
                response = await llm.chat(
                    [HumanMessage(content=prompt_input)],
                    system=_DOCSTRING_PROMPT,
                )
                draft = str(response.content)
                diff: str | None = _unified_diff(existing_content, draft, target_path) or None
                mode: DocMode = "docstring"

            else:
                # README / doc mode — determine greenfield vs update
                mode = "update" if existing_content else "greenfield"

                tree_raw = await _call_tool(
                    tools,
                    "list_directory_contents",
                    {"owner": owner, "repo": repo, "path": ""},
                )
                file_tree = _summarize_file_tree(tree_raw)

                prompt_input = _readme_context(owner, repo, meta_raw, file_tree, existing_content)
                response = await llm.chat(
                    [HumanMessage(content=prompt_input)],
                    system=_README_PROMPT,
                )
                draft = str(response.content)
                diff = (
                    _unified_diff(existing_content, draft, target_path) or None
                    if existing_content
                    else None
                )

            result = DocWriteResult(
                owner=owner,
                repo=repo,
                target_path=target_path,
                mode=mode,
                draft=draft,
                diff=diff,
            )

            artifacts: dict[str, Any] = dict(state.get("artifacts") or {})
            artifacts["doc_write"] = result.model_dump()

            reply = AIMessage(content=result.model_dump_json(indent=2))

            # Gate writing back behind HITL — only when there is something to write
            hitl_request: HITLRequest | None = None
            has_changes = mode == "greenfield" or bool(diff)
            if has_changes:
                branch = f"devhub/docs-{target_path.replace('/', '-')}-{uuid.uuid4().hex[:8]}"
                hitl_request = HITLRequest(
                    id=uuid.uuid4(),
                    prompt=(
                        f"Create a PR on {owner}/{repo} to write the following to "
                        f"`{target_path}` (branch: `{branch}`)?\n\n"
                        + (f"Diff:\n```diff\n{diff}\n```" if diff else "(new file)")
                    ),
                    tool_name="create_pull_request_with_file",
                    tool_args={
                        "owner": owner,
                        "repo": repo,
                        "path": target_path,
                        "branch": branch,
                        "content": draft,
                        "commit_message": f"docs: update {target_path}",
                        "pr_title": f"docs: update {target_path}",
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
                agent="doc_writer",
                retryable=False,
            )
            return Command(
                goto="supervisor",
                update={"errors": [error], "current_agent": "supervisor"},
            )

    return doc_writer
