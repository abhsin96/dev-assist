"""Typed error hierarchy for DevHub.

Every error carries a machine-readable ``code``, an HTTP status, and a
``user_message`` that is safe to surface in API responses.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from enum import StrEnum


class ErrorCode(StrEnum):
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    MCP_ERROR = "MCP_ERROR"
    MCP_TOOL_TIMEOUT = "MCP_TOOL_TIMEOUT"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    AGENT_ERROR = "AGENT_ERROR"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"


class DevHubError(Exception):
    code: str = ErrorCode.INTERNAL_ERROR
    http_status: int = 500
    user_message: str = "An unexpected error occurred"
    retriable: bool = False

    def __init__(
        self,
        user_message: str | None = None,
        *,
        cause: Exception | None = None,
        retry_after: int | None = None,
    ) -> None:
        self.user_message = user_message or type(self).user_message
        self.cause = cause
        self.retry_after = retry_after
        super().__init__(self.user_message)


class ValidationError(DevHubError):
    code = ErrorCode.VALIDATION_ERROR
    http_status = 422
    user_message = "Invalid input"


class AuthError(DevHubError):
    code = ErrorCode.AUTH_ERROR
    http_status = 401
    user_message = "Authentication required"


class PermissionError(DevHubError):
    code = ErrorCode.PERMISSION_ERROR
    http_status = 403
    user_message = "You do not have permission to perform this action"


class NotFoundError(DevHubError):
    code = ErrorCode.NOT_FOUND_ERROR
    http_status = 404
    user_message = "Resource not found"


class RateLimitError(DevHubError):
    code = ErrorCode.RATE_LIMIT_ERROR
    http_status = 429
    user_message = "Too many requests"
    retriable = True


class MCPError(DevHubError):
    code = ErrorCode.MCP_ERROR
    http_status = 502
    user_message = "Tool call failed"
    retriable = True


class MCPToolTimeoutError(MCPError):
    code = ErrorCode.MCP_TOOL_TIMEOUT
    user_message = "Tool call timed out"


class ToolNotAllowedError(MCPError):
    code = ErrorCode.TOOL_NOT_ALLOWED
    http_status = 403
    user_message = "Agent is not permitted to use this tool"
    retriable = False


class ApprovalRequiredError(MCPError):
    code = ErrorCode.APPROVAL_REQUIRED
    http_status = 403
    user_message = "This tool requires human approval before execution"
    retriable = False


class AgentError(DevHubError):
    code = ErrorCode.AGENT_ERROR
    http_status = 500
    user_message = "Agent encountered an error"


class AuthRequiredError(DevHubError):
    """Raised when an OAuth-connected provider token is missing or revoked."""

    code = ErrorCode.AUTH_REQUIRED
    http_status = 401
    user_message = "OAuth connection required. Please connect your account in Settings."


class UpstreamError(DevHubError):
    code = ErrorCode.UPSTREAM_ERROR
    http_status = 502
    user_message = "Upstream service error"
    retriable = True


_DEFAULT_RETRIABLE: frozenset[str] = frozenset(
    {ErrorCode.MCP_ERROR, ErrorCode.MCP_TOOL_TIMEOUT, ErrorCode.UPSTREAM_ERROR}
)


async def with_retries[T](
    fn: Callable[[], Awaitable[T]],
    *,
    retriable_codes: frozenset[str] = _DEFAULT_RETRIABLE,
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> T:
    """Retry ``fn`` with exponential back-off + jitter on retriable errors.

    Non-retriable errors and errors whose code is not in ``retriable_codes``
    are re-raised immediately without consuming retry budget.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except DevHubError as exc:
            if not exc.retriable or exc.code not in retriable_codes:
                raise
            last_exc = exc
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.1)
                await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]
