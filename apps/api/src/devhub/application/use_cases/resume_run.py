"""ResumeRun use-case: continue a graph run from its latest checkpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage

from devhub.application.use_cases.run_events import DoneEvent, ErrorEvent, RunEvent, TokenEvent
from devhub.core.errors import NotFoundError
from devhub.domain.ports import IRunRepository


class ResumeRunUseCase:
    def __init__(self, graph: Any, run_repo: IRunRepository) -> None:
        self._graph = graph
        self._run_repo = run_repo

    async def execute(self, run_id: uuid.UUID) -> AsyncIterator[RunEvent]:
        run = await self._run_repo.get(run_id)
        if run is None:
            raise NotFoundError(f"Run {run_id} not found")
        return self._stream(run_id, run.thread_id)

    async def _stream(self, run_id: uuid.UUID, thread_id: uuid.UUID) -> AsyncIterator[RunEvent]:
        config = {"configurable": {"thread_id": str(thread_id)}}
        final_text = ""

        try:
            async for event in self._graph.astream_events(
                None,
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield TokenEvent(text=str(chunk.content))
                        final_text += str(chunk.content)

                elif kind == "on_chain_end":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        for err in output.get("errors", []):
                            yield ErrorEvent(
                                code=getattr(err, "code", "AGENT_ERROR"),
                                message=getattr(err, "message", str(err)),
                                retryable=getattr(err, "retryable", False),
                            )
                        for msg in output.get("messages", []):
                            if isinstance(msg, AIMessage) and msg.content:
                                final_text = str(msg.content)

        except Exception as exc:
            await self._run_repo.mark_failed(
                run_id, {"code": "INTERNAL_ERROR", "message": str(exc)}
            )
            yield ErrorEvent(code="INTERNAL_ERROR", message="Resume failed unexpectedly")
            return

        await self._run_repo.mark_completed(run_id)
        yield DoneEvent(run_id=run_id, final_message=final_text)
