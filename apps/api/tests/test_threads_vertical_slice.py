"""Vertical slice: GET /threads → ListThreadsUseCase → IThreadRepository (fake).

Demonstrates that the hexagonal layering works: the router wires a real use-case
to a fake repo — no database needed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from devhub.api.deps import get_list_threads_use_case
from devhub.application.use_cases.list_threads import ListThreadsUseCase
from devhub.domain.models import Thread
from devhub.domain.ports import IThreadRepository
from devhub.main import app

_USER_ID = uuid.uuid4()
_NOW = datetime(2026, 1, 1, tzinfo=UTC)

_SAMPLE_THREAD = Thread(
    id=uuid.uuid4(),
    user_id=_USER_ID,
    title="Hello world",
    created_at=_NOW,
    updated_at=_NOW,
)


class FakeThreadRepository:
    """In-memory implementation of IThreadRepository for testing."""

    def __init__(self, threads: list[Thread]) -> None:
        self._threads = threads

    async def list_for_user(self, user_id: uuid.UUID) -> list[Thread]:
        return [t for t in self._threads if t.user_id == user_id]

    async def get(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None:
        return next(
            (t for t in self._threads if t.id == thread_id and t.user_id == user_id),
            None,
        )


assert isinstance(FakeThreadRepository([]), IThreadRepository)  # structural check


def _make_fake_use_case_override() -> ListThreadsUseCase:
    return ListThreadsUseCase(FakeThreadRepository([_SAMPLE_THREAD]))


@pytest.fixture()
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Patch JWT decode where deps.py imported it so the bearer token is bypassed."""
    import devhub.api.deps as deps_mod

    monkeypatch.setattr(
        deps_mod,
        "decode_api_token",
        lambda _token: {"sub": str(_USER_ID), "email": "test@example.com"},
    )
    return {"Authorization": "Bearer fake-token"}


@pytest.mark.asyncio
async def test_list_threads_returns_users_threads(
    auth_headers: dict[str, str],
) -> None:
    app.dependency_overrides[get_list_threads_use_case] = _make_fake_use_case_override

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/threads", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(get_list_threads_use_case, None)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Hello world"
    assert body[0]["user_id"] == str(_USER_ID)


@pytest.mark.asyncio
async def test_list_threads_requires_auth() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/threads")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
