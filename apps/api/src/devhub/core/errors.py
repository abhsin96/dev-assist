"""Typed error hierarchy for DevHub.

Every error carries a machine-readable ``code``, an HTTP status, and a
``user_message`` that is safe to surface in API responses.
"""

from __future__ import annotations


class DevHubError(Exception):
    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    user_message: str = "An unexpected error occurred"
    retriable: bool = False

    def __init__(
        self,
        user_message: str | None = None,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.user_message = user_message or type(self).user_message
        self.cause = cause
        super().__init__(self.user_message)


class ValidationError(DevHubError):
    code = "VALIDATION_ERROR"
    http_status = 422
    user_message = "Invalid input"


class AuthError(DevHubError):
    code = "AUTH_ERROR"
    http_status = 401
    user_message = "Authentication required"


class MCPError(DevHubError):
    code = "MCP_ERROR"
    http_status = 502
    user_message = "Tool call failed"
    retriable = True


class AgentError(DevHubError):
    code = "AGENT_ERROR"
    http_status = 500
    user_message = "Agent encountered an error"


class UpstreamError(DevHubError):
    code = "UPSTREAM_ERROR"
    http_status = 502
    user_message = "Upstream service error"
    retriable = True
