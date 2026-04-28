"""Unit tests for RFC 7807 error handlers.

Covers three paths:
1. Known DevHubError → correct problem+json shape
2. Unknown exception → sanitised 500 (no internals leaked)
3. Pydantic RequestValidationError → 422 with normalised errors[]
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from devhub.api.error_handlers import register_error_handlers
from devhub.core.errors import AuthError, MCPError, NotFoundError


@pytest.fixture()
def client() -> TestClient:
    """Minimal app with error handlers and three test routes."""
    _app = FastAPI()
    register_error_handlers(_app)

    @_app.get("/raise/auth")
    async def raise_auth() -> None:
        raise AuthError("Token is expired")

    @_app.get("/raise/mcp")
    async def raise_mcp() -> None:
        raise MCPError("GitHub tool timed out")

    @_app.get("/raise/not-found")
    async def raise_not_found() -> None:
        raise NotFoundError("Thread not found")

    @_app.get("/raise/unhandled")
    async def raise_unhandled() -> None:
        raise RuntimeError("secret db password in trace")

    @_app.post("/raise/validation")
    async def raise_validation(body: ValidationModel) -> dict[str, str]:
        return {"name": body.name}

    return TestClient(_app, raise_server_exceptions=False)


from pydantic import BaseModel  # noqa: E402


class ValidationModel(BaseModel):
    name: str
    age: int


# ── Known DevHubError ─────────────────────────────────────────────────────────


def test_auth_error_shape(client: TestClient) -> None:
    r = client.get("/raise/auth")
    assert r.status_code == 401
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["code"] == "AUTH_ERROR"
    assert body["status"] == 401
    assert body["detail"] == "Token is expired"
    assert body["type"] == "https://devhub.ai/errors/AUTH_ERROR"
    assert "traceId" in body
    assert "instance" in body


def test_mcp_error_shape(client: TestClient) -> None:
    r = client.get("/raise/mcp")
    assert r.status_code == 502
    body = r.json()
    assert body["code"] == "MCP_ERROR"
    assert body["detail"] == "GitHub tool timed out"


def test_not_found_error_shape(client: TestClient) -> None:
    r = client.get("/raise/not-found")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "NOT_FOUND_ERROR"


# ── Unknown exception → sanitised 500 ────────────────────────────────────────


def test_unhandled_error_is_sanitised(client: TestClient) -> None:
    r = client.get("/raise/unhandled")
    assert r.status_code == 500
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["code"] == "INTERNAL_ERROR"
    # Must not leak the original exception message
    assert "secret" not in r.text
    assert "RuntimeError" not in r.text
    assert "traceId" in body


# ── Pydantic validation error → normalised 422 ───────────────────────────────


def test_validation_error_normalised(client: TestClient) -> None:
    # Send request missing required fields
    r = client.post("/raise/validation", json={})
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "errors" in body
    errors = body["errors"]
    assert isinstance(errors, list)
    assert len(errors) > 0
    assert "path" in errors[0]
    assert "message" in errors[0]


def test_validation_error_partial(client: TestClient) -> None:
    # age is wrong type
    r = client.post("/raise/validation", json={"name": "Alice", "age": "not-a-number"})
    assert r.status_code == 422
    body = r.json()
    assert any("age" in e["path"] for e in body["errors"])


# ── with_retries helper ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_with_retries_succeeds_on_first_try() -> None:
    from devhub.core.errors import with_retries

    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retries(flaky)
    assert result == "ok"
    assert calls == 1


@pytest.mark.asyncio
async def test_with_retries_retries_retriable_error() -> None:
    from devhub.core.errors import MCPError, with_retries

    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise MCPError("transient")
        return "ok"

    result = await with_retries(flaky, base_delay=0.0)
    assert result == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_with_retries_raises_non_retriable_immediately() -> None:
    from devhub.core.errors import AuthError, with_retries

    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        raise AuthError("not retriable")

    with pytest.raises(AuthError):
        await with_retries(flaky, base_delay=0.0)

    assert calls == 1


@pytest.mark.asyncio
async def test_with_retries_exhausts_budget() -> None:
    from devhub.core.errors import MCPError, with_retries

    calls = 0

    async def always_fails() -> str:
        nonlocal calls
        calls += 1
        raise MCPError("always")

    with pytest.raises(MCPError):
        await with_retries(always_fails, max_attempts=3, base_delay=0.0)

    assert calls == 3
