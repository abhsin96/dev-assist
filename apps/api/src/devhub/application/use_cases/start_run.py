"""StartRun use-case: create a run, stream graph events, persist result."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from devhub.application.use_cases.run_events import DoneEvent, ErrorEvent, RunEvent, TokenEvent
from devhub.domain.ports import IRunRepository


class StartRunUseCase:
    def __init__(self, graph: Any, run_repo: IRunRepository) -> None:
        self._graph = graph
        self._run_repo = run_repo

    async def execute(self, thread_id: uuid.UUID, user_message: str) -> AsyncIterator[RunEvent]:
        return self._stream(thread_id, user_message)

    async def _stream(self, thread_id: uuid.UUID, user_message: str) -> AsyncIterator[RunEvent]:
        run = await self._run_repo.create(thread_id)
        config = {"configurable": {"thread_id": str(thread_id)}}
        final_text = ""
        error_events: list[ErrorEvent] = []

        try:
            async for event in self._graph.astream_events(
                {"messages": [HumanMessage(content=user_message)]},
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
                        errors = output.get("errors", [])
                        for err in errors:
                            ev = ErrorEvent(
                                code=getattr(err, "code", "AGENT_ERROR"),
                                message=getattr(err, "message", str(err)),
                                retryable=getattr(err, "retryable", False),
                            )
                            error_events.append(ev)
                            yield ev

                        msgs = output.get("messages", [])
                        for msg in msgs:
                            if isinstance(msg, AIMessage) and msg.content:
                                final_text = str(msg.content)

        except Exception as exc:
            await self._run_repo.mark_failed(
                run.id, {"code": "INTERNAL_ERROR", "message": str(exc)}
            )
            yield ErrorEvent(code="INTERNAL_ERROR", message="Run failed unexpectedly")
            return

        if error_events:
            await self._run_repo.mark_failed(
                run.id,
                {"code": error_events[-1].code, "message": error_events[-1].message},
            )
        else:
            await self._run_repo.mark_completed(run.id)

        yield DoneEvent(run_id=run.id, final_message=final_text)
