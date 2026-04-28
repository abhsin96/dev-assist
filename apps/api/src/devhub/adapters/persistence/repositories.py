from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.models import Thread as OrmThread
from devhub.adapters.persistence.models import User as OrmUser
from devhub.domain.models import Thread, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, email: str, name: str | None, avatar_url: str | None) -> User:
        stmt = (
            pg_insert(OrmUser)
            .values(email=email, name=name, avatar_url=avatar_url)
            .on_conflict_do_update(
                index_elements=["email"],
                set_={"name": name, "avatar_url": avatar_url},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        result = await self._session.execute(select(OrmUser).where(OrmUser.email == email))
        orm = result.scalar_one()
        return _user_to_domain(orm)


class ThreadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[Thread]:
        result = await self._session.execute(
            select(OrmThread)
            .where(OrmThread.user_id == user_id)
            .order_by(OrmThread.updated_at.desc())
        )
        return [_thread_to_domain(row) for row in result.scalars().all()]

    async def get(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Thread | None:
        result = await self._session.execute(
            select(OrmThread).where(OrmThread.id == thread_id, OrmThread.user_id == user_id)
        )
        orm = result.scalar_one_or_none()
        return _thread_to_domain(orm) if orm else None


def _user_to_domain(orm: OrmUser) -> User:
    return User(
        id=orm.id,
        email=orm.email,
        name=orm.name,
        avatar_url=orm.avatar_url,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _thread_to_domain(orm: OrmThread) -> Thread:
    return Thread(
        id=orm.id,
        user_id=orm.user_id,
        title=orm.title,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
