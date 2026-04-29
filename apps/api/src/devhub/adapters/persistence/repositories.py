from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.models import Run as OrmRun
from devhub.adapters.persistence.models import Thread as OrmThread
from devhub.adapters.persistence.models import User as OrmUser
from devhub.domain.models import Run, Thread, User


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

    async def create(self, user_id: uuid.UUID, title: str) -> Thread:
        orm = OrmThread(user_id=user_id, title=title)
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _thread_to_domain(orm)

    async def update(self, thread_id: uuid.UUID, title: str) -> Thread:
        from datetime import UTC, datetime

        from sqlalchemy import update

        await self._session.execute(
            update(OrmThread)
            .where(OrmThread.id == thread_id)
            .values(title=title, updated_at=datetime.now(UTC))
        )
        await self._session.commit()
        result = await self._session.execute(select(OrmThread).where(OrmThread.id == thread_id))
        orm = result.scalar_one()
        return _thread_to_domain(orm)

    async def delete(self, thread_id: uuid.UUID) -> None:
        from sqlalchemy import delete

        await self._session.execute(delete(OrmThread).where(OrmThread.id == thread_id))
        await self._session.commit()


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


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, thread_id: uuid.UUID) -> Run:
        orm = OrmRun(thread_id=thread_id, status="running")
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return _run_to_domain(orm)

    async def get(self, run_id: uuid.UUID) -> Run | None:
        result = await self._session.execute(select(OrmRun).where(OrmRun.id == run_id))
        orm = result.scalar_one_or_none()
        return _run_to_domain(orm) if orm else None

    async def mark_completed(self, run_id: uuid.UUID) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        await self._session.execute(
            update(OrmRun)
            .where(OrmRun.id == run_id)
            .values(status="completed", finished_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def mark_failed(self, run_id: uuid.UUID, error_data: dict[str, object]) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        await self._session.execute(
            update(OrmRun)
            .where(OrmRun.id == run_id)
            .values(status="failed", finished_at=datetime.now(UTC), error_data=error_data)
        )
        await self._session.commit()


def _run_to_domain(orm: OrmRun) -> Run:
    return Run(
        id=orm.id,
        thread_id=orm.thread_id,
        status=orm.status,  # type: ignore[arg-type]
        started_at=orm.started_at,
        finished_at=orm.finished_at,
        error_data=orm.error_data,
    )


class HITLApprovalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        run_id: uuid.UUID,
        tool_call: dict[str, object],
        summary: str,
        risk: str,
        expires_at: object,
    ) -> object:
        from devhub.adapters.persistence.models import HITLApproval as OrmHITLApproval
        from devhub.domain.models import HITLApproval

        orm = OrmHITLApproval(
            run_id=run_id,
            tool_call=tool_call,
            summary=summary,
            risk=risk,
            expires_at=expires_at,
        )
        self._session.add(orm)
        await self._session.commit()
        await self._session.refresh(orm)
        return HITLApproval(
            id=orm.id,
            run_id=orm.run_id,
            tool_call=orm.tool_call,
            summary=orm.summary,
            risk=orm.risk,  # type: ignore[arg-type]
            status=orm.status,  # type: ignore[arg-type]
            expires_at=orm.expires_at,
            created_at=orm.created_at,
            resolved_at=orm.resolved_at,
            decision=orm.decision,  # type: ignore[arg-type]
            patched_args=orm.patched_args,
        )

    async def get(self, approval_id: uuid.UUID) -> object | None:
        from devhub.adapters.persistence.models import HITLApproval as OrmHITLApproval
        from devhub.domain.models import HITLApproval

        result = await self._session.execute(
            select(OrmHITLApproval).where(OrmHITLApproval.id == approval_id)
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return HITLApproval(
            id=orm.id,
            run_id=orm.run_id,
            tool_call=orm.tool_call,
            summary=orm.summary,
            risk=orm.risk,  # type: ignore[arg-type]
            status=orm.status,  # type: ignore[arg-type]
            expires_at=orm.expires_at,
            created_at=orm.created_at,
            resolved_at=orm.resolved_at,
            decision=orm.decision,  # type: ignore[arg-type]
            patched_args=orm.patched_args,
        )

    async def resolve(
        self,
        approval_id: uuid.UUID,
        decision: str,
        patched_args: dict[str, object] | None = None,
    ) -> None:
        from datetime import UTC, datetime

        from sqlalchemy import update

        from devhub.adapters.persistence.models import HITLApproval as OrmHITLApproval

        status = "approved" if decision == "approve" else "rejected"
        await self._session.execute(
            update(OrmHITLApproval)
            .where(OrmHITLApproval.id == approval_id)
            .values(
                status=status,
                decision=decision,
                patched_args=patched_args,
                resolved_at=datetime.now(UTC),
            )
        )
        await self._session.commit()

    async def expire_pending(self) -> list[uuid.UUID]:
        from datetime import UTC, datetime

        from sqlalchemy import update

        from devhub.adapters.persistence.models import HITLApproval as OrmHITLApproval

        now = datetime.now(UTC)
        result = await self._session.execute(
            select(OrmHITLApproval.id).where(
                OrmHITLApproval.status == "pending", OrmHITLApproval.expires_at < now
            )
        )
        expired_ids = [row[0] for row in result.all()]
        if expired_ids:
            await self._session.execute(
                update(OrmHITLApproval)
                .where(OrmHITLApproval.id.in_(expired_ids))
                .values(status="expired", decision="reject", resolved_at=now)
            )
            await self._session.commit()
        return expired_ids


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_approval(
        self,
        user_id: uuid.UUID,
        approval_id: uuid.UUID,
        decision: str,
        patched_args: dict[str, object] | None,
    ) -> None:
        from devhub.adapters.persistence.models import AuditLog as OrmAuditLog

        orm = OrmAuditLog(
            user_id=user_id,
            approval_id=approval_id,
            decision=decision,
            patched_args=patched_args,
        )
        self._session.add(orm)
        await self._session.commit()
