"""Port interfaces — abstract contracts that adapters must satisfy.

All protocols use structural subtyping (``typing.Protocol``) so adapters
never import from this module; they just match the shape.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from devhub.domain.models import Thread, User


@runtime_checkable
class IUserRepository(Protocol):
    async def upsert(self, email: str, name: str | None, avatar_url: str | None) -> User: ...


@runtime_checkable
class IThreadRepository(Protocol):
    async def list_for_user(self, user_id: uuid.UUID) -> list[Thread]: ...

    async def get(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None: ...


@runtime_checkable
class IMCPRegistry(Protocol):
    async def is_healthy(self) -> bool: ...


@runtime_checkable
class ILLMClient(Protocol):
    async def is_healthy(self) -> bool: ...
