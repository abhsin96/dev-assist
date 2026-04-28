from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from devhub.api.deps import CurrentUser, get_list_threads_use_case
from devhub.application.use_cases.list_threads import ListThreadsUseCase
from devhub.domain.models import Thread

router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=list[Thread])
async def list_threads(
    current_user: CurrentUser,
    use_case: Annotated[ListThreadsUseCase, Depends(get_list_threads_use_case)],
) -> list[Thread]:
    user_id = uuid.UUID(str(current_user["sub"]))
    return await use_case.execute(user_id)
