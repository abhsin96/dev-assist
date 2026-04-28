"""Per-run event store: append-only log with live subscriber fan-out.

Each run gets its own _RunStore. Subscribers receive past events replayed
from *from_seq*, then live events as they arrive. A ``None`` sentinel is
yielded every _HEARTBEAT_INTERVAL seconds of silence to keep SSE connections
alive through proxies.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator

from devhub.application.use_cases.run_events import RunEvent

_QUEUE_CAPACITY = 256
_HEARTBEAT_INTERVAL = 15.0
_TERMINAL_TYPES = frozenset({"done", "error"})


class EventEnvelope:
    __slots__ = ("seq", "run_id", "event")

    def __init__(self, seq: int, run_id: uuid.UUID, event: RunEvent) -> None:
        self.seq = seq
        self.run_id = run_id
        self.event = event


class _RunStore:
    def __init__(self) -> None:
        self._log: list[EventEnvelope] = []
        self._queues: set[asyncio.Queue[EventEnvelope | None]] = set()
        self._done = False

    def append(self, envelope: EventEnvelope) -> None:
        self._log.append(envelope)
        if envelope.event.type in _TERMINAL_TYPES:
            self._done = True
        for q in list(self._queues):
            with contextlib.suppress(asyncio.QueueFull):  # slow consumer — drop, don't block
                q.put_nowait(envelope)

    def snapshot_from(self, seq: int) -> list[EventEnvelope]:
        return [e for e in self._log if e.seq >= seq]

    @property
    def done(self) -> bool:
        return self._done

    def add_subscriber(self) -> asyncio.Queue[EventEnvelope | None]:
        q: asyncio.Queue[EventEnvelope | None] = asyncio.Queue(maxsize=_QUEUE_CAPACITY)
        self._queues.add(q)
        return q

    def remove_subscriber(self, q: asyncio.Queue[EventEnvelope | None]) -> None:
        self._queues.discard(q)
        # Unblock any waiting get() so the subscriber coroutine can exit
        with contextlib.suppress(asyncio.QueueFull):
            q.put_nowait(None)


class EventStore:
    """In-process event store keyed by run_id."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, _RunStore] = {}
        self._lock = asyncio.Lock()

    async def _get_store(self, run_id: uuid.UUID) -> _RunStore:
        async with self._lock:
            if run_id not in self._runs:
                self._runs[run_id] = _RunStore()
            return self._runs[run_id]

    async def publish(self, run_id: uuid.UUID, event: RunEvent) -> None:
        store = await self._get_store(run_id)
        # seq is assigned under the store's internal ordering (not thread-safe
        # across concurrent publishers, but runs are single-writer by design)
        envelope = EventEnvelope(seq=len(store._log), run_id=run_id, event=event)
        store.append(envelope)

    async def subscribe(
        self, run_id: uuid.UUID, from_seq: int = 0
    ) -> AsyncIterator[EventEnvelope | None]:
        """Yield envelopes from *from_seq* onward.

        ``None`` is yielded as a heartbeat signal every _HEARTBEAT_INTERVAL
        seconds of silence. The iterator terminates automatically after a
        terminal event (``done`` or ``error``).
        """
        store = await self._get_store(run_id)

        # Register queue BEFORE snapshot to close the replay/live-tail race window.
        q = store.add_subscriber()
        seen_seq = from_seq - 1

        try:
            for envelope in store.snapshot_from(from_seq):
                yield envelope
                seen_seq = envelope.seq
                if envelope.event.type in _TERMINAL_TYPES:
                    return

            if store.done:
                return

            while True:
                try:
                    envelope = await asyncio.wait_for(q.get(), timeout=_HEARTBEAT_INTERVAL)  # type: ignore[arg-type]
                except TimeoutError:
                    yield None  # heartbeat
                    continue

                if envelope is None:
                    return  # sentinel — store removed us

                if envelope.seq > seen_seq:
                    seen_seq = envelope.seq
                    yield envelope

                if envelope.event.type in _TERMINAL_TYPES:
                    return
        finally:
            store.remove_subscriber(q)
