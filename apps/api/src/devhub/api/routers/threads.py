from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from devhub.api.deps import (
    CurrentUserId,
    get_create_thread_use_case,
    get_delete_thread_use_case,
    get_get_thread_use_case,
    get_graph,
    get_list_threads_use_case,
    get_update_thread_use_case,
)
from devhub.application.use_cases.create_thread import CreateThreadUseCase
from devhub.application.use_cases.delete_thread import DeleteThreadUseCase
from devhub.application.use_cases.get_thread import GetThreadUseCase
from devhub.application.use_cases.list_threads import ListThreadsUseCase
from devhub.application.use_cases.update_thread import UpdateThreadUseCase
from devhub.domain.models import Thread

router = APIRouter(prefix="/threads", tags=["threads"])


class CreateThreadRequest(BaseModel):
    title: str = "New conversation"


class UpdateThreadRequest(BaseModel):
    title: str


class ThreadMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


@router.get("", response_model=list[Thread])
async def list_threads(
    user_id: CurrentUserId,
    use_case: Annotated[ListThreadsUseCase, Depends(get_list_threads_use_case)],
) -> list[Thread]:
    return await use_case.execute(user_id)


@router.post("", response_model=Thread, status_code=201)
async def create_thread(
    user_id: CurrentUserId,
    request: CreateThreadRequest,
    use_case: Annotated[CreateThreadUseCase, Depends(get_create_thread_use_case)],
) -> Thread:
    return await use_case.execute(user_id, request.title)


@router.get("/{thread_id}", response_model=Thread)
async def get_thread(
    thread_id: uuid.UUID,
    user_id: CurrentUserId,
    use_case: Annotated[GetThreadUseCase, Depends(get_get_thread_use_case)],
) -> Thread:
    thread = await use_case.execute(thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.patch("/{thread_id}", response_model=Thread)
async def update_thread(
    thread_id: uuid.UUID,
    user_id: CurrentUserId,
    request: UpdateThreadRequest,
    use_case: Annotated[UpdateThreadUseCase, Depends(get_update_thread_use_case)],
) -> Thread:
    thread = await use_case.execute(thread_id, user_id, request.title)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.get("/{thread_id}/messages", response_model=list[ThreadMessage])
async def get_thread_messages(
    thread_id: uuid.UUID,
    user_id: CurrentUserId,
    graph: Annotated[Any, Depends(get_graph)],
    use_case: Annotated[GetThreadUseCase, Depends(get_get_thread_use_case)],
) -> list[ThreadMessage]:
    thread = await use_case.execute(thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    config = {"configurable": {"thread_id": str(thread_id)}}
    state = await graph.aget_state(config)
    if not state or not state.values:
        return []

    result: list[ThreadMessage] = []
    for msg in state.values.get("messages", []):
        content = getattr(msg, "content", "")
        if not content:
            continue
        if isinstance(msg, HumanMessage):
            result.append(ThreadMessage(role="user", content=str(content)))
        elif isinstance(msg, AIMessage):
            result.append(ThreadMessage(role="assistant", content=str(content)))
    return result


@router.delete("/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: uuid.UUID,
    user_id: CurrentUserId,
    use_case: Annotated[DeleteThreadUseCase, Depends(get_delete_thread_use_case)],
) -> None:
    success = await use_case.execute(thread_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")
