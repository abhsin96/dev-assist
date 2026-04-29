"""ORM models for per-user OAuth connector tokens and audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from devhub.adapters.persistence.models import Base


class OAuthConnection(Base):
    """Stores AES-GCM–encrypted access/refresh tokens scoped to (user_id, provider).

    Raw token bytes are NEVER logged or returned in API responses.
    """

    __tablename__ = "oauth_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    encrypted_access_token: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="")
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_oauth_conn_user_provider"),)

    def __repr__(self) -> str:
        return f"<OAuthConnection id={self.id} provider={self.provider} user={self.user_id}>"


class OAuthAuditLog(Base):
    """Immutable audit trail for connect / refresh / revoke events."""

    __tablename__ = "oauth_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
