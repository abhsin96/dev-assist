from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class Thread(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


RunStatus = Literal["pending", "running", "completed", "failed"]


class Run(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    error_data: dict[str, Any] | None = None


# ── MCP value objects ─────────────────────────────────────────────────────────


class MCPServerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    server_id: str
    url: str
    transport: Literal["streamable-http"] = "streamable-http"
    enabled: bool = True
    config: dict[str, Any] | None = None


class MCPServerInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    server_id: str
    url: str
    connected: bool
    enabled: bool
    tool_count: int
    tools: list[str] = []
    config: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    last_connected_at: datetime | None = None


class MCPServerCreate(BaseModel):
    server_id: str
    url: str
    transport: Literal["streamable-http"] = "streamable-http"
    config: dict[str, Any] | None = None


class MCPServerUpdate(BaseModel):
    url: str | None = None
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class ToolCall(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    args: dict[str, Any]
    agent_id: str
    approval_id: str | None = None


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_name: str
    ok: bool
    data: Any = None
    error: str | None = None


class PRReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    summary: str
    blocking: list[str]
    non_blocking: list[str]
    nits: list[str]
    suggested_comment: str


# ── Issue triage value objects ────────────────────────────────────────────────

IssuePriority = Literal["P0", "P1", "P2", "P3"]


class IssueTriage(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue_number: int
    title: str
    priority: IssuePriority
    labels: list[str]
    duplicate_of: int | None
    suggested_assignee: str | None
    rationale: str


class IssueTriageResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str
    triaged: list[IssueTriage]
    cache_hits: int


# ── Doc writer value objects ──────────────────────────────────────────────────

DocMode = Literal["greenfield", "update", "docstring"]


class DocWriteResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    owner: str
    repo: str
    target_path: str
    mode: DocMode
    draft: str
    diff: str | None


# ── Code search value objects ─────────────────────────────────────────────────

CodeSearchSource = Literal["github", "vector", "merged"]


class CodeSearchHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo: str
    path: str
    start_line: int
    end_line: int
    snippet: str
    score: float
    source: CodeSearchSource


class CodeSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    hits: list[CodeSearchHit]
    total: int


# ── HITL value objects ────────────────────────────────────────────────────────

ApprovalDecision = Literal["approve", "reject"]
ApprovalStatus = Literal["pending", "approved", "rejected", "expired"]
RiskLevel = Literal["low", "medium", "high"]


class HITLRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: uuid.UUID
    run_id: uuid.UUID
    tool_call: ToolCall
    summary: str
    risk: RiskLevel
    expires_at: datetime


class ApprovalSubmission(BaseModel):
    approval_id: uuid.UUID
    decision: ApprovalDecision
    patched_args: dict[str, Any] | None = None


class HITLApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    run_id: uuid.UUID
    tool_call: dict[str, Any]
    summary: str
    risk: RiskLevel
    status: ApprovalStatus
    expires_at: datetime
    created_at: datetime
    resolved_at: datetime | None = None
    decision: ApprovalDecision | None = None
    patched_args: dict[str, Any] | None = None


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    user_id: uuid.UUID
    approval_id: uuid.UUID
    decision: ApprovalDecision
    patched_args: dict[str, Any] | None
    timestamp: datetime


# ── OAuth connector value objects ─────────────────────────────────────────────

OAuthProvider = Literal["github", "slack"]
OAuthEvent = Literal["connect", "refresh", "revoke"]


class OAuthConnection(BaseModel):
    """Public metadata for an OAuth connector — never includes raw token bytes."""

    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: OAuthProvider
    scope: str
    connected_at: datetime
    token_expires_at: datetime | None = None
    revoked_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
