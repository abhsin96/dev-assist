"""SSE encoding and stream generator for run events."""

from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import AsyncIterator

from devhub.adapters.streaming.event_store import EventEnvelope, EventStore


def _json_default(obj: object) -> str:
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def encode_sse(envelope: EventEnvelope) -> dict[str, str]:
    """Encode a run event envelope as an sse-starlette event dict."""
    payload = dataclasses.asdict(envelope.event)
    return {
        "id": str(envelope.seq),
        "event": envelope.event.type,
        "data": json.dumps(payload, default=_json_default),
    }


async def run_event_stream(
    event_store: EventStore,
    run_id: uuid.UUID,
    from_seq: int = 0,
) -> AsyncIterator[dict[str, str]]:
    """Yield sse-starlette event dicts for a run, interleaved with heartbeats."""
    async for item in event_store.subscribe(run_id, from_seq):
        if item is None:
            yield {"event": "heartbeat", "data": ""}
        else:
            yield encode_sse(item)
