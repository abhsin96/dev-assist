"""OAuthConnectionRepository — persists encrypted tokens and audit events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.models.oauth_connections import (
    OAuthAuditLog as OrmOAuthAuditLog,
)
from devhub.adapters.persistence.models.oauth_connections import (
    OAuthConnection as OrmOAuthConnection,
)
from devhub.domain.models import OAuthConnection, OAuthEvent, OAuthProvider


class OAuthConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Write ─────────────────────────────────────────────────────────────────

    async def upsert(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes | None,
        scope: str,
        token_expires_at: object | None,
    ) -> OAuthConnection:
        stmt = (
            pg_insert(OrmOAuthConnection)
            .values(
                user_id=user_id,
                provider=provider,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                scope=scope,
                token_expires_at=token_expires_at,
                revoked_at=None,
            )
            .on_conflict_do_update(
                constraint="uq_oauth_conn_user_provider",
                set_={
                    "encrypted_access_token": encrypted_access_token,
                    "encrypted_refresh_token": encrypted_refresh_token,
                    "scope": scope,
                    "token_expires_at": token_expires_at,
                    "revoked_at": None,
                    "connected_at": func_now(),
                },
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return await self._fetch(user_id, provider)  # type: ignore[return-value]

    async def update_tokens(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes | None,
        token_expires_at: object | None,
    ) -> None:
        from sqlalchemy import update

        await self._session.execute(
            update(OrmOAuthConnection)
            .where(
                OrmOAuthConnection.user_id == user_id,
                OrmOAuthConnection.provider == provider,
            )
            .values(
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                token_expires_at=token_expires_at,
            )
        )
        await self._session.commit()

    async def revoke(self, user_id: uuid.UUID, provider: OAuthProvider) -> None:
        from sqlalchemy import update

        await self._session.execute(
            update(OrmOAuthConnection)
            .where(
                OrmOAuthConnection.user_id == user_id,
                OrmOAuthConnection.provider == provider,
            )
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def audit(self, user_id: uuid.UUID, provider: OAuthProvider, event: OAuthEvent) -> None:
        orm = OrmOAuthAuditLog(user_id=user_id, provider=provider, event=event)
        self._session.add(orm)
        await self._session.commit()

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get(self, user_id: uuid.UUID, provider: OAuthProvider) -> OAuthConnection | None:
        return await self._fetch(user_id, provider)

    async def get_encrypted_tokens(
        self, user_id: uuid.UUID, provider: OAuthProvider
    ) -> tuple[bytes, bytes | None] | None:
        result = await self._session.execute(
            select(OrmOAuthConnection).where(
                OrmOAuthConnection.user_id == user_id,
                OrmOAuthConnection.provider == provider,
                OrmOAuthConnection.revoked_at.is_(None),
            )
        )
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return orm.encrypted_access_token, orm.encrypted_refresh_token

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthConnection]:
        result = await self._session.execute(
            select(OrmOAuthConnection)
            .where(
                OrmOAuthConnection.user_id == user_id,
                OrmOAuthConnection.revoked_at.is_(None),
            )
            .order_by(OrmOAuthConnection.connected_at.desc())
        )
        return [_to_domain(row) for row in result.scalars().all()]

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _fetch(self, user_id: uuid.UUID, provider: OAuthProvider) -> OAuthConnection | None:
        result = await self._session.execute(
            select(OrmOAuthConnection).where(
                OrmOAuthConnection.user_id == user_id,
                OrmOAuthConnection.provider == provider,
            )
        )
        orm = result.scalar_one_or_none()
        return _to_domain(orm) if orm else None


def _to_domain(orm: OrmOAuthConnection) -> OAuthConnection:
    return OAuthConnection(
        id=orm.id,
        user_id=orm.user_id,
        provider=orm.provider,  # type: ignore[arg-type]
        scope=orm.scope,
        connected_at=orm.connected_at,
        token_expires_at=orm.token_expires_at,
        revoked_at=orm.revoked_at,
    )


def func_now() -> datetime:
    return datetime.now(UTC)
