from __future__ import annotations

import uuid

from devhub.domain.models import Thread
from devhub.domain.ports import IThreadRepository


class GetThreadUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None:
        return await self._repo.get(thread_id, user_id)
