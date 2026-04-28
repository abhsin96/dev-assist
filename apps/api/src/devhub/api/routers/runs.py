"""Runs API: start a run and stream its events via SSE."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from devhub.adapters.streaming.event_store import EventStore
from devhub.adapters.streaming.sse import run_event_stream
from devhub.api.deps import CurrentUser, get_event_store, get_graph, get_run_repo, get_thread_repo
from devhub.core.errors import NotFoundError
from devhub.domain.ports import IRunRepository, IThreadRepository

router = APIRouter(tags=["runs"])


class StartRunRequest(BaseModel):
    message: str


class StartRunResponse(BaseModel):
    run_id: uuid.UUID


@router.post("/threads/{thread_id}/runs", response_model=StartRunResponse, status_code=202)
async def start_run(
    thread_id: uuid.UUID,
    body: StartRunRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    run_repo: Annotated[IRunRepository, Depends(get_run_repo)],
    thread_repo: Annotated[IThreadRepository, Depends(get_thread_repo)],
    graph: Annotated[Any, Depends(get_graph)],
    event_store: Annotated[EventStore, Depends(get_event_store)],
) -> StartRunResponse:
    user_id = uuid.UUID(str(user["sub"]))
    thread = await thread_repo.get(thread_id, user_id)
    if thread is None:
        raise NotFoundError("Thread not found")

    run = await run_repo.create(thread_id)
    background_tasks.add_task(
        _run_and_publish,
        run.id,
        thread_id,
        body.message,
        graph,
        event_store,
    )
    return StartRunResponse(run_id=run.id)


@router.get("/runs/{run_id}/events")
async def get_run_events(
    run_id: uuid.UUID,
    request: Request,
    _user: CurrentUser,
    event_store: Annotated[EventStore, Depends(get_event_store)],
    from_seq: int = Query(default=0, alias="from", ge=0),
) -> EventSourceResponse:
    async def _generator() -> Any:
        async for chunk in run_event_stream(event_store, run_id, from_seq):
            if await request.is_disconnected():
                break
            yield chunk

    return EventSourceResponse(_generator())


async def _run_and_publish(
    run_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_message: str,
    graph: Any,
    event_store: EventStore,
) -> None:
    """Background task: stream the graph and fan-out events to subscribers."""
    from langchain_core.messages import AIMessage, HumanMessage

    from devhub.adapters.persistence.database import get_session_factory
    from devhub.adapters.persistence.repositories import RunRepository
    from devhub.application.use_cases.run_events import DoneEvent, ErrorEvent, TokenEvent

    config = {"configurable": {"thread_id": str(thread_id)}}
    final_text = ""
    error_seen = False

    async with get_session_factory()() as session:
        run_repo = RunRepository(session)
        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=user_message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        await event_store.publish(run_id, TokenEvent(text=str(chunk.content)))
                        final_text += str(chunk.content)

                elif kind == "on_chain_end":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict):
                        for err in output.get("errors", []):
                            await event_store.publish(
                                run_id,
                                ErrorEvent(
                                    code=getattr(err, "code", "AGENT_ERROR"),
                                    message=getattr(err, "message", str(err)),
                                    retryable=getattr(err, "retryable", False),
                                ),
                            )
                            error_seen = True

                        for msg in output.get("messages", []):
                            if isinstance(msg, AIMessage) and msg.content:
                                final_text = str(msg.content)

        except Exception as exc:
            await event_store.publish(
                run_id,
                ErrorEvent(code="INTERNAL_ERROR", message=str(exc)),
            )
            await run_repo.mark_failed(run_id, {"code": "INTERNAL_ERROR", "message": str(exc)})
            return

        if error_seen:
            await run_repo.mark_failed(run_id, {"code": "AGENT_ERROR", "message": "Agent error"})
        else:
            await run_repo.mark_completed(run_id)

        await event_store.publish(run_id, DoneEvent(run_id=run_id, final_message=final_text))
