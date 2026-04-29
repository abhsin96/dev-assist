from __future__ import annotations

import uuid

from devhub.domain.models import Thread
from devhub.domain.ports import IThreadRepository


class CreateThreadUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: uuid.UUID, title: str = "New conversation") -> Thread:
        return await self._repo.create(user_id, title)
