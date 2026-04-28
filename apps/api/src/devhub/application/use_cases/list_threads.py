from __future__ import annotations

import uuid

from devhub.domain.models import Thread
from devhub.domain.ports import IThreadRepository


class ListThreadsUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: uuid.UUID) -> list[Thread]:
        return await self._repo.list_for_user(user_id)
