from __future__ import annotations

import uuid

from devhub.domain.ports import IThreadRepository


class DeleteThreadUseCase:
    def __init__(self, repo: IThreadRepository) -> None:
        self._repo = repo

    async def execute(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        # Verify ownership
        existing = await self._repo.get(thread_id, user_id)
        if not existing:
            return False

        await self._repo.delete(thread_id)
        return True
