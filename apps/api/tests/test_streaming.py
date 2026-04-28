"""Tests for EventStore, SSE encoding, and the /runs endpoints.

Uses an in-memory event store; no real graph or DB required.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from devhub.adapters.streaming.event_store import EventStore
from devhub.adapters.streaming.sse import encode_sse, run_event_stream
from devhub.application.use_cases.run_events import DoneEvent, TokenEvent

# ── EventStore ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_then_subscribe_replays_history() -> None:
    store = EventStore()
    run_id = uuid.uuid4()

    await store.publish(run_id, TokenEvent(text="hello"))
    await store.publish(run_id, TokenEvent(text=" world"))

    events = []
    async for item in store.subscribe(run_id, from_seq=0):
        if item is not None:
            events.append(item)
        if len(events) == 2:
            break

    assert len(events) == 2
    assert events[0].event.type == "token"
    assert events[0].seq == 0
    assert events[1].seq == 1


@pytest.mark.asyncio
async def test_subscribe_from_seq_skips_earlier_events() -> None:
    store = EventStore()
    run_id = uuid.uuid4()

    await store.publish(run_id, TokenEvent(text="a"))
    await store.publish(run_id, TokenEvent(text="b"))
    await store.publish(run_id, TokenEvent(text="c"))

    events = []
    async for item in store.subscribe(run_id, from_seq=1):
        if item is not None:
            events.append(item)
        if len(events) == 2:
            break

    assert len(events) == 2
    assert events[0].seq == 1
    assert events[1].seq == 2


@pytest.mark.asyncio
async def test_terminal_done_event_ends_subscription() -> None:
    store = EventStore()
    run_id = uuid.uuid4()
    done = DoneEvent(run_id=run_id, final_message="bye")

    await store.publish(run_id, TokenEvent(text="hi"))
    await store.publish(run_id, done)

    events = []
    async for item in store.subscribe(run_id, from_seq=0):
        if item is not None:
            events.append(item)

    assert len(events) == 2
    assert events[-1].event.type == "done"


@pytest.mark.asyncio
async def test_live_publish_reaches_subscriber() -> None:
    store = EventStore()
    run_id = uuid.uuid4()
    received: list[str] = []

    async def _subscriber() -> None:
        async for item in store.subscribe(run_id, from_seq=0):
            if item is not None:
                received.append(item.event.type)
                if item.event.type == "done":
                    break

    task = asyncio.create_task(_subscriber())
    await asyncio.sleep(0)  # let subscriber register

    await store.publish(run_id, TokenEvent(text="streaming"))
    await store.publish(run_id, DoneEvent(run_id=run_id, final_message="ok"))
    await asyncio.wait_for(task, timeout=2.0)

    assert received == ["token", "done"]


# ── SSE encoding ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_encode_sse_token_event() -> None:
    store = EventStore()
    run_id = uuid.uuid4()
    await store.publish(run_id, TokenEvent(text="hi"))

    envelopes = []
    async for item in store.subscribe(run_id, from_seq=0):
        if item is not None:
            envelopes.append(item)
        break

    encoded = encode_sse(envelopes[0])
    assert encoded["event"] == "token"
    assert encoded["id"] == "0"
    payload = json.loads(encoded["data"])
    assert payload["text"] == "hi"
    assert payload["type"] == "token"


@pytest.mark.asyncio
async def test_encode_sse_done_event_serializes_uuid() -> None:
    store = EventStore()
    run_id = uuid.uuid4()
    await store.publish(run_id, DoneEvent(run_id=run_id, final_message="fin"))

    envelopes = []
    async for item in store.subscribe(run_id, from_seq=0):
        if item is not None:
            envelopes.append(item)
        break

    encoded = encode_sse(envelopes[0])
    payload = json.loads(encoded["data"])
    assert payload["run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_run_event_stream_yields_encoded_events() -> None:
    store = EventStore()
    run_id = uuid.uuid4()
    await store.publish(run_id, TokenEvent(text="x"))
    await store.publish(run_id, DoneEvent(run_id=run_id, final_message="done"))

    chunks = []
    async for chunk in run_event_stream(store, run_id, from_seq=0):
        chunks.append(chunk)

    assert any(c["event"] == "token" for c in chunks)
    assert any(c["event"] == "done" for c in chunks)


# ── HTTP endpoint tests ───────────────────────────────────────────────────────

_USER_ID = uuid.uuid4()
_THREAD_ID = uuid.uuid4()


@pytest.fixture()
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    import devhub.api.deps as deps_mod

    monkeypatch.setattr(
        deps_mod,
        "decode_api_token",
        lambda _token: {"sub": str(_USER_ID), "email": "test@example.com"},
    )
    return {"Authorization": "Bearer fake"}


@pytest.mark.asyncio
async def test_start_run_returns_run_id(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from httpx import ASGITransport, AsyncClient

    import devhub.api.routers.runs as runs_mod
    from devhub.api.deps import get_event_store, get_graph, get_run_repo, get_thread_repo
    from devhub.main import app

    run_id = uuid.uuid4()
    mock_thread = MagicMock(id=_THREAD_ID, user_id=_USER_ID)
    mock_run = MagicMock(id=run_id)
    mock_thread_repo = AsyncMock()
    mock_thread_repo.get = AsyncMock(return_value=mock_thread)
    mock_run_repo = AsyncMock()
    mock_run_repo.create = AsyncMock(return_value=mock_run)

    monkeypatch.setattr(runs_mod, "_run_and_publish", AsyncMock())

    app.dependency_overrides[get_thread_repo] = lambda: mock_thread_repo
    app.dependency_overrides[get_run_repo] = lambda: mock_run_repo
    app.dependency_overrides[get_graph] = lambda: MagicMock()
    app.dependency_overrides[get_event_store] = lambda: MagicMock()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/threads/{_THREAD_ID}/runs",
                json={"message": "hello"},
                headers=auth_headers,
            )
    finally:
        for key in [get_thread_repo, get_run_repo, get_graph, get_event_store]:
            app.dependency_overrides.pop(key, None)

    assert resp.status_code == 202
    assert "run_id" in resp.json()


@pytest.mark.asyncio
async def test_start_run_returns_404_for_unknown_thread(
    auth_headers: dict[str, str],
) -> None:
    from httpx import ASGITransport, AsyncClient

    from devhub.api.deps import get_event_store, get_graph, get_run_repo, get_thread_repo
    from devhub.main import app

    mock_thread_repo = AsyncMock()
    mock_thread_repo.get = AsyncMock(return_value=None)

    app.dependency_overrides[get_thread_repo] = lambda: mock_thread_repo
    app.dependency_overrides[get_run_repo] = lambda: AsyncMock()
    app.dependency_overrides[get_graph] = lambda: MagicMock()
    app.dependency_overrides[get_event_store] = lambda: MagicMock()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/threads/{_THREAD_ID}/runs",
                json={"message": "hello"},
                headers=auth_headers,
            )
    finally:
        for key in [get_thread_repo, get_run_repo, get_graph, get_event_store]:
            app.dependency_overrides.pop(key, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_events_streams_sse(
    auth_headers: dict[str, str],
) -> None:
    from httpx import ASGITransport, AsyncClient

    from devhub.api.deps import get_event_store
    from devhub.main import app

    run_id = uuid.uuid4()
    store = EventStore()
    await store.publish(run_id, TokenEvent(text="stream"))
    await store.publish(run_id, DoneEvent(run_id=run_id, final_message="done"))

    app.dependency_overrides[get_event_store] = lambda: store

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/runs/{run_id}/events",
                headers=auth_headers,
            )
    finally:
        app.dependency_overrides.pop(get_event_store, None)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "token" in resp.text
    assert "done" in resp.text
