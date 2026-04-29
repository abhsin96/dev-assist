"""OAuth connector flow — GitHub and Slack.

Endpoints:
  GET  /connect/{provider}/start     — redirect to provider consent screen
  GET  /connect/{provider}/callback  — exchange code, encrypt + store tokens
  DELETE /connect/{provider}         — revoke token at provider, delete local copy
  GET  /connect                      — list active connections for current user
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.auth.cipher import decrypt_token, encrypt_token
from devhub.adapters.cache.redis import get_redis
from devhub.adapters.oauth.providers import (
    OAuthTokens,
    build_auth_url,
    exchange_code,
    refresh_tokens,
    revoke_token,
)
from devhub.adapters.persistence.database import get_db
from devhub.adapters.persistence.repositories.oauth_connection_repository import (
    OAuthConnectionRepository,
)
from devhub.api.deps import CurrentUser
from devhub.core.errors import AuthRequiredError
from devhub.core.logging import get_logger
from devhub.core.settings import get_settings
from devhub.domain.models import OAuthConnection, OAuthProvider

logger = get_logger(__name__)

router = APIRouter(prefix="/connect", tags=["oauth"])

_STATE_TTL = 600  # 10 minutes
_REFRESH_BUFFER_SECS = 300  # refresh when within 5 minutes of expiry

_VALID_PROVIDERS: frozenset[OAuthProvider] = frozenset({"github", "slack"})


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_valid_provider(provider: str) -> OAuthProvider:
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider '{provider}'. Supported: github, slack",
        )
    return provider  # mypy narrows str via frozenset[OAuthProvider] membership check above


def _state_key(token: str) -> str:
    return f"oauth_state:{token}"


def _redirect_uri(provider: OAuthProvider, request_base_url: str) -> str:
    settings = get_settings()
    base = (
        settings.frontend_url
        if not request_base_url.startswith("http://test")
        else request_base_url.rstrip("/")
    )
    return f"{base}/api/connect/{provider}/callback"


async def _get_valid_access_token(
    user_id: uuid.UUID,
    provider: OAuthProvider,
    repo: OAuthConnectionRepository,
) -> str:
    """Return a valid decrypted access token, refreshing automatically if near-expiry."""
    settings = get_settings()
    tokens = await repo.get_encrypted_tokens(user_id, provider)
    if tokens is None:
        raise AuthRequiredError(f"No active {provider} connection. Connect in Settings.")

    enc_access, enc_refresh = tokens
    connection = await repo.get(user_id, provider)

    if (
        connection is not None
        and connection.token_expires_at is not None
        and enc_refresh is not None
    ):
        secs_until_expiry = (connection.token_expires_at - datetime.now(UTC)).total_seconds()
        if secs_until_expiry < _REFRESH_BUFFER_SECS:
            raw_refresh = decrypt_token(settings.oauth_encryption_key, enc_refresh)
            new_tokens = await refresh_tokens(provider, raw_refresh, settings)
            new_enc_access, new_enc_refresh, new_expires_at = _pack_tokens(new_tokens, settings)
            await repo.update_tokens(
                user_id, provider, new_enc_access, new_enc_refresh, new_expires_at
            )
            await repo.audit(user_id, provider, "refresh")
            logger.info("oauth.token_refreshed", provider=provider, user_id=str(user_id))
            return new_tokens.access_token

    return decrypt_token(settings.oauth_encryption_key, enc_access)


def _pack_tokens(tokens: OAuthTokens, settings: Any) -> tuple[bytes, bytes | None, datetime | None]:
    enc_access = encrypt_token(settings.oauth_encryption_key, tokens.access_token)
    enc_refresh: bytes | None = None
    if tokens.refresh_token:
        enc_refresh = encrypt_token(settings.oauth_encryption_key, tokens.refresh_token)
    expires_at: datetime | None = None
    if tokens.expires_in is not None:
        expires_at = datetime.now(UTC) + timedelta(seconds=tokens.expires_in)
    return enc_access, enc_refresh, expires_at


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/{provider}/start")
async def oauth_start(
    provider: str,
    claims: CurrentUser,
    redis: Annotated[Redis, Depends(get_redis)],
) -> RedirectResponse:
    """Generate state, store in Redis, redirect to provider consent screen."""
    prov = _assert_valid_provider(provider)
    settings = get_settings()

    user_id = str(claims["sub"])
    state_token = os.urandom(24).hex()
    state = f"{user_id}:{state_token}"

    await redis.setex(_state_key(state_token), _STATE_TTL, user_id)

    redirect_uri = f"{settings.frontend_url}/api/connect/{prov}/callback"
    url = build_auth_url(prov, state, redirect_uri, settings)

    logger.info("oauth.start", provider=prov, user_id=user_id)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    redis: Annotated[Redis, Depends(get_redis)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RedirectResponse:
    """Validate state, exchange code, encrypt tokens, persist, redirect to frontend."""
    prov = _assert_valid_provider(provider)
    settings = get_settings()

    # Parse state: "{user_id}:{state_token}"
    parts = state.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state")

    user_id_str, state_token = parts
    stored = await redis.get(_state_key(state_token))
    if stored is None or stored != user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state"
        )
    await redis.delete(_state_key(state_token))

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed state"
        ) from None

    redirect_uri = f"{settings.frontend_url}/api/connect/{prov}/callback"
    try:
        tokens = await exchange_code(prov, code, redirect_uri, settings)
    except Exception as exc:
        logger.error("oauth.exchange_failed", provider=prov, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Token exchange failed",
        ) from exc

    enc_access, enc_refresh, expires_at = _pack_tokens(tokens, settings)

    repo = OAuthConnectionRepository(db)
    await repo.upsert(user_id, prov, enc_access, enc_refresh, tokens.scope, expires_at)
    await repo.audit(user_id, prov, "connect")

    logger.info("oauth.connected", provider=prov, user_id=user_id_str)
    return RedirectResponse(
        url=f"{settings.frontend_url}/settings/connections?connected={prov}",
        status_code=status.HTTP_302_FOUND,
    )


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def oauth_revoke(
    provider: str,
    claims: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Invalidate token at provider, mark local connection revoked, audit."""
    prov = _assert_valid_provider(provider)
    settings = get_settings()
    user_id = uuid.UUID(str(claims["sub"]))

    repo = OAuthConnectionRepository(db)
    tokens = await repo.get_encrypted_tokens(user_id, prov)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active {prov} connection",
        )

    enc_access, _ = tokens
    access_token = decrypt_token(settings.oauth_encryption_key, enc_access)

    try:
        await revoke_token(prov, access_token, settings)
    except Exception as exc:
        logger.warning(
            "oauth.provider_revoke_failed",
            provider=prov,
            error=str(exc),
        )

    await repo.revoke(user_id, prov)
    await repo.audit(user_id, prov, "revoke")
    logger.info("oauth.revoked", provider=prov, user_id=str(user_id))


@router.get("", response_model=list[dict[str, Any]])
async def list_connections(
    claims: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    """Return active OAuth connections for the authenticated user."""
    user_id = uuid.UUID(str(claims["sub"]))
    repo = OAuthConnectionRepository(db)
    connections: list[OAuthConnection] = await repo.list_for_user(user_id)
    return [
        {
            "provider": c.provider,
            "scope": c.scope,
            "connected_at": c.connected_at.isoformat(),
            "token_expires_at": c.token_expires_at.isoformat() if c.token_expires_at else None,
        }
        for c in connections
    ]
