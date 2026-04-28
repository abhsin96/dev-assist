from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, email: str, name: str | None, avatar_url: str | None) -> User:
        stmt = (
            pg_insert(User)
            .values(email=email, name=name, avatar_url=avatar_url)
            .on_conflict_do_update(
                index_elements=["email"],
                set_={"name": name, "avatar_url": avatar_url},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one()
