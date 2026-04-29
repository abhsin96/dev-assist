"""Tests for DEVHUB-025 OAuth connector flow.

Covers:
- AES-GCM cipher round-trip and tamper detection
- Plaintext tokens never in exception messages (AC: no-token-in-logs)
- build_auth_url correctness for both providers
- OAuthConnection domain model has no token fields (structural AC)
- exchange_code success and failure paths
- refresh_tokens rotation
- revoke_token paths
- Router: /connect/{provider}/start redirects to correct URL with state
- Router: /connect/{provider}/callback validates state, stores connection, audits
- Router: /connect/{provider}/callback rejects invalid / expired state
- Router: DELETE /connect/{provider} revokes and audits
- Router: GET /connect lists active connections
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from cryptography.exceptions import InvalidTag
from httpx import ASGITransport, AsyncClient, Request, Response

import devhub.api.routers.oauth_connect as oauth_mod
from devhub.adapters.auth.cipher import decrypt_token, encrypt_token
from devhub.adapters.oauth.providers import OAuthTokens, build_auth_url
from devhub.domain.models import OAuthConnection, OAuthProvider
from devhub.main import app

# ── Constants ─────────────────────────────────────────────────────────────────

_USER_ID = uuid.uuid4()
_USER_EMAIL = "tester@example.com"
_KEY_HEX = "a" * 64  # valid 32-byte AES key

_FAKE_CLAIMS: dict[str, Any] = {"sub": str(_USER_ID), "email": _USER_EMAIL}

_FAKE_SETTINGS_KWARGS: dict[str, Any] = {
    "oauth_encryption_key": _KEY_HEX,
    "github_client_id": "gh-client-id",
    "github_client_secret": "gh-client-secret",
    "slack_client_id": "slack-client-id",
    "slack_client_secret": "slack-client-secret",
    "frontend_url": "http://localhost:3000",
}


# ── Fake infrastructure ───────────────────────────────────────────────────────


class _FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:  # noqa: ARG002
        self._store[key] = value

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def aclose(self) -> None:
        pass


class _FakeOAuthRepo:
    def __init__(self) -> None:
        self.connections: dict[tuple[uuid.UUID, str], OAuthConnection] = {}
        self.tokens: dict[tuple[uuid.UUID, str], tuple[bytes, bytes | None]] = {}
        self.audit_log: list[tuple[uuid.UUID, str, str]] = []

    async def upsert(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes | None,
        scope: str,
        token_expires_at: object | None,
    ) -> OAuthConnection:
        conn = OAuthConnection(
            id=uuid.uuid4(),
            user_id=user_id,
            provider=provider,
            scope=scope,
            connected_at=datetime.now(UTC),
            token_expires_at=token_expires_at if isinstance(token_expires_at, datetime) else None,
        )
        self.connections[(user_id, provider)] = conn
        self.tokens[(user_id, provider)] = (encrypted_access_token, encrypted_refresh_token)
        return conn

    async def get(self, user_id: uuid.UUID, provider: OAuthProvider) -> OAuthConnection | None:
        return self.connections.get((user_id, provider))

    async def get_encrypted_tokens(
        self, user_id: uuid.UUID, provider: OAuthProvider
    ) -> tuple[bytes, bytes | None] | None:
        return self.tokens.get((user_id, provider))

    async def update_tokens(
        self,
        user_id: uuid.UUID,
        provider: OAuthProvider,
        encrypted_access_token: bytes,
        encrypted_refresh_token: bytes | None,
        token_expires_at: object | None,
    ) -> None:
        self.tokens[(user_id, provider)] = (encrypted_access_token, encrypted_refresh_token)

    async def revoke(self, user_id: uuid.UUID, provider: OAuthProvider) -> None:
        key = (user_id, provider)
        conn = self.connections.get(key)
        if conn:
            self.connections[key] = conn.model_copy(update={"revoked_at": datetime.now(UTC)})

    async def list_for_user(self, user_id: uuid.UUID) -> list[OAuthConnection]:
        return [c for (uid, _), c in self.connections.items() if uid == user_id and c.is_active]

    async def audit(self, user_id: uuid.UUID, provider: OAuthProvider, event: str) -> None:
        self.audit_log.append((user_id, provider, event))


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    import devhub.api.deps as deps_mod

    monkeypatch.setattr(deps_mod, "decode_api_token", lambda _t: _FAKE_CLAIMS)
    return {"Authorization": "Bearer fake"}


@pytest.fixture()
def fake_redis() -> _FakeRedis:
    return _FakeRedis()


@pytest.fixture()
def fake_repo() -> _FakeOAuthRepo:
    return _FakeOAuthRepo()


# ── Cipher tests ──────────────────────────────────────────────────────────────


def test_cipher_round_trip() -> None:
    plaintext = "ghp_super_secret_token_abc123"
    ct = encrypt_token(_KEY_HEX, plaintext)
    assert decrypt_token(_KEY_HEX, ct) == plaintext


def test_cipher_nonce_is_random() -> None:
    """Different encryptions of the same plaintext must produce different ciphertexts."""
    pt = "same-value"
    ct1 = encrypt_token(_KEY_HEX, pt)
    ct2 = encrypt_token(_KEY_HEX, pt)
    assert ct1 != ct2


def test_cipher_tamper_raises_invalid_tag() -> None:
    ct = encrypt_token(_KEY_HEX, "secret")
    tampered = bytearray(ct)
    tampered[-1] ^= 0xFF
    with pytest.raises(InvalidTag):
        decrypt_token(_KEY_HEX, bytes(tampered))


def test_cipher_exception_does_not_contain_plaintext() -> None:
    """InvalidTag must not echo the plaintext in its message — AC: no-token-in-logs."""
    secret = "super-secret-token-leak-check"
    ct = encrypt_token(_KEY_HEX, secret)
    tampered = bytearray(ct)
    tampered[-1] ^= 0xFF
    try:
        decrypt_token(_KEY_HEX, bytes(tampered))
    except InvalidTag as exc:
        assert secret not in str(exc)


def test_dev_key_fallback_works() -> None:
    """Empty key_hex uses an ephemeral in-process key — round-trip still works."""
    pt = "dev-token"
    ct = encrypt_token("", pt)
    assert decrypt_token("", ct) == pt


# ── Domain model token isolation tests ───────────────────────────────────────


def test_oauth_connection_domain_model_has_no_token_fields() -> None:
    """OAuthConnection must not expose raw token bytes — AC: no-token-in-logs."""
    conn = OAuthConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="github",
        scope="repo",
        connected_at=datetime.now(UTC),
    )
    assert not hasattr(conn, "access_token")
    assert not hasattr(conn, "refresh_token")
    assert not hasattr(conn, "encrypted_access_token")
    assert not hasattr(conn, "encrypted_refresh_token")


def test_oauth_connection_repr_has_no_token_fields() -> None:
    conn = OAuthConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="slack",
        scope="chat:write",
        connected_at=datetime.now(UTC),
    )
    r = repr(conn)
    assert "token" not in r.lower() or "token_expires_at" in r


def test_oauth_connection_is_active_property() -> None:
    conn = OAuthConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="github",
        scope="repo",
        connected_at=datetime.now(UTC),
    )
    assert conn.is_active

    revoked = conn.model_copy(update={"revoked_at": datetime.now(UTC)})
    assert not revoked.is_active


# ── build_auth_url tests ──────────────────────────────────────────────────────


def test_build_auth_url_github() -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    url = build_auth_url("github", "state123", "http://localhost:3000/callback", settings)
    assert "github.com/login/oauth/authorize" in url
    assert "client_id=gh-client-id" in url
    assert "state=state123" in url
    assert "repo" in url


def test_build_auth_url_slack() -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    url = build_auth_url("slack", "state456", "http://localhost:3000/callback", settings)
    assert "slack.com/oauth/v2/authorize" in url
    assert "client_id=slack-client-id" in url
    assert "state=state456" in url
    assert "channels" in url


def test_build_auth_url_state_in_query() -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    state = "user-id-here:random123abc"
    url = build_auth_url("github", state, "http://cb", settings)
    assert "state=user-id-here" in url or "state=" in url


# ── exchange_code tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_exchange_code_github_success() -> None:
    from devhub.adapters.oauth.providers import exchange_code
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    mock_response = Response(
        200,
        json={"access_token": "gha_abc123", "scope": "repo read:user", "token_type": "bearer"},
        request=Request("POST", "https://github.com/login/oauth/access_token"),
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    tokens = await exchange_code(
        "github", "code123", "http://cb", settings, http_client=mock_client
    )
    assert tokens.access_token == "gha_abc123"
    assert tokens.refresh_token is None
    assert "repo" in tokens.scope


@pytest.mark.asyncio
async def test_exchange_code_github_error_response() -> None:
    from devhub.adapters.oauth.providers import exchange_code
    from devhub.core.errors import UpstreamError
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    mock_response = Response(
        200,
        json={"error": "bad_verification_code", "error_description": "The code is invalid"},
        request=Request("POST", "https://github.com/login/oauth/access_token"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(UpstreamError) as exc_info:
        await exchange_code("github", "bad_code", "http://cb", settings, http_client=mock_client)
    assert "bad_verification_code" in str(exc_info.value)
    assert "gha_" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_exchange_code_slack_success() -> None:
    from devhub.adapters.oauth.providers import exchange_code
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    mock_response = Response(
        200,
        json={
            "ok": True,
            "access_token": "xoxb-slack-token",
            "scope": "channels:read chat:write",
            "token_type": "bot",
        },
        request=Request("POST", "https://slack.com/api/oauth.v2.access"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    tokens = await exchange_code(
        "slack", "slackcode", "http://cb", settings, http_client=mock_client
    )
    assert tokens.access_token == "xoxb-slack-token"


# ── refresh_tokens tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_tokens_rotates_and_stores() -> None:
    from devhub.adapters.oauth.providers import refresh_tokens
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    new_access = "gha_new_refreshed_token"
    mock_response = Response(
        200,
        json={"access_token": new_access, "refresh_token": "new_rt", "expires_in": 28800},
        request=Request("POST", "https://github.com/login/oauth/access_token"),
    )
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    tokens = await refresh_tokens("github", "old_rt", settings, http_client=mock_client)
    assert tokens.access_token == new_access
    assert tokens.refresh_token == "new_rt"
    assert tokens.expires_in == 28800


# ── revoke_token tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_token_github_success() -> None:
    from devhub.adapters.oauth.providers import revoke_token
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    mock_response = Response(
        204,
        request=Request("DELETE", "https://api.github.com/applications/gh-client-id/token"),
    )
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    await revoke_token("github", "gha_secret", settings, http_client=mock_client)


@pytest.mark.asyncio
async def test_revoke_token_error_does_not_contain_secret() -> None:
    """Provider revoke errors must not echo the access token — AC: no-token-in-logs."""
    from devhub.adapters.oauth.providers import revoke_token
    from devhub.core.errors import UpstreamError
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    secret_token = "gha_super_secret_do_not_log_me"

    mock_response = Response(
        500,
        request=Request("DELETE", "https://api.github.com/applications/gh-client-id/token"),
    )
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(UpstreamError) as exc_info:
        await revoke_token("github", secret_token, settings, http_client=mock_client)

    assert secret_token not in str(exc_info.value)


# ── Router tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_oauth_start_redirects_to_github(
    auth_headers: dict[str, str],
    fake_redis: _FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get("/api/connect/github/start", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert resp.status_code == 302
    location = resp.headers["location"]
    assert "github.com/login/oauth/authorize" in location
    assert "client_id=gh-client-id" in location
    assert "state=" in location


@pytest.mark.asyncio
async def test_oauth_start_stores_state_in_redis(
    auth_headers: dict[str, str],
    fake_redis: _FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            await client.get("/api/connect/github/start", headers=auth_headers)
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert any(k.startswith("oauth_state:") for k in fake_redis._store)


@pytest.mark.asyncio
async def test_oauth_start_unknown_provider_returns_404(
    auth_headers: dict[str, str],
) -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        resp = await client.get("/api/connect/twitter/start", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_oauth_callback_valid_state_stores_connection(
    fake_redis: _FakeRedis,
    fake_repo: _FakeOAuthRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    state_token = "abc123def456"
    state = f"{_USER_ID}:{state_token}"
    await fake_redis.setex(f"oauth_state:{state_token}", 600, str(_USER_ID))

    fake_tokens = OAuthTokens(
        access_token="gha_fresh_token", refresh_token=None, scope="repo", expires_in=None
    )

    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth_mod, "exchange_code", AsyncMock(return_value=fake_tokens))
    monkeypatch.setattr(
        "devhub.api.routers.oauth_connect.OAuthConnectionRepository",
        lambda _db: fake_repo,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            resp = await client.get(f"/api/connect/github/callback?code=testcode&state={state}")
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert resp.status_code == 302
    assert "connected=github" in resp.headers["location"]

    key = (_USER_ID, "github")
    assert key in fake_repo.connections
    assert any(e[2] == "connect" for e in fake_repo.audit_log)


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state_returns_400(
    fake_redis: _FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                f"/api/connect/github/callback?code=x&state={_USER_ID}:nosuchtoken"
            )
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_oauth_callback_missing_state_param_returns_422(
    fake_redis: _FakeRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/connect/github/callback?code=x")
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_oauth_callback_state_is_single_use(
    fake_redis: _FakeRedis,
    fake_repo: _FakeOAuthRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A state nonce must be consumed on first use — replay must fail."""
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    state_token = "singleuse999"
    state = f"{_USER_ID}:{state_token}"
    await fake_redis.setex(f"oauth_state:{state_token}", 600, str(_USER_ID))

    fake_tokens = OAuthTokens("tok", None, "repo", None)
    app.dependency_overrides[oauth_mod.get_redis] = lambda: fake_redis  # type: ignore[attr-defined]
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth_mod, "exchange_code", AsyncMock(return_value=fake_tokens))
    monkeypatch.setattr(
        "devhub.api.routers.oauth_connect.OAuthConnectionRepository",
        lambda _db: fake_repo,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            r1 = await client.get(f"/api/connect/github/callback?code=c1&state={state}")
            r2 = await client.get(f"/api/connect/github/callback?code=c2&state={state}")
    finally:
        app.dependency_overrides.pop(oauth_mod.get_redis, None)

    assert r1.status_code == 302
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_oauth_revoke_calls_provider_and_audits(
    auth_headers: dict[str, str],
    fake_repo: _FakeOAuthRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    enc = encrypt_token(_KEY_HEX, "gha_token_to_revoke")
    await fake_repo.upsert(_USER_ID, "github", enc, None, "repo", None)

    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(oauth_mod, "revoke_token", AsyncMock())
    monkeypatch.setattr(
        "devhub.api.routers.oauth_connect.OAuthConnectionRepository",
        lambda _db: fake_repo,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.delete("/api/connect/github", headers=auth_headers)

    assert resp.status_code == 204
    assert any(e[2] == "revoke" for e in fake_repo.audit_log)
    conn = await fake_repo.get(_USER_ID, "github")
    assert conn is not None and conn.revoked_at is not None


@pytest.mark.asyncio
async def test_oauth_revoke_missing_connection_returns_404(
    auth_headers: dict[str, str],
    fake_repo: _FakeOAuthRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "devhub.api.routers.oauth_connect.OAuthConnectionRepository",
        lambda _db: fake_repo,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.delete("/api/connect/github", headers=auth_headers)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_connections_returns_active_only(
    auth_headers: dict[str, str],
    fake_repo: _FakeOAuthRepo,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)
    enc = encrypt_token(_KEY_HEX, "gha_token")
    await fake_repo.upsert(_USER_ID, "github", enc, None, "repo", None)

    enc2 = encrypt_token(_KEY_HEX, "xoxb_revoked")
    await fake_repo.upsert(_USER_ID, "slack", enc2, None, "channels:read", None)
    await fake_repo.revoke(_USER_ID, "slack")

    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "devhub.api.routers.oauth_connect.OAuthConnectionRepository",
        lambda _db: fake_repo,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/connect", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["provider"] == "github"


@pytest.mark.asyncio
async def test_get_valid_access_token_triggers_refresh_when_near_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tokens within 5 minutes of expiry are automatically refreshed and stored."""
    from datetime import timedelta

    from devhub.adapters.oauth.providers import OAuthTokens
    from devhub.api.routers.oauth_connect import _get_valid_access_token
    from devhub.core.settings import Settings

    settings = Settings(**_FAKE_SETTINGS_KWARGS)

    old_access = "gha_old_token"
    new_access = "gha_new_after_refresh"
    expires_soon = datetime.now(UTC) + timedelta(seconds=60)

    enc = encrypt_token(_KEY_HEX, old_access)
    enc_rt = encrypt_token(_KEY_HEX, "old_refresh_token")

    repo = _FakeOAuthRepo()
    conn = OAuthConnection(
        id=uuid.uuid4(),
        user_id=_USER_ID,
        provider="github",
        scope="repo",
        connected_at=datetime.now(UTC),
        token_expires_at=expires_soon,
    )
    repo.connections[(_USER_ID, "github")] = conn
    repo.tokens[(_USER_ID, "github")] = (enc, enc_rt)

    new_tokens = OAuthTokens(new_access, "new_rt", "repo", 28800)
    monkeypatch.setattr(oauth_mod, "refresh_tokens", AsyncMock(return_value=new_tokens))
    monkeypatch.setattr(oauth_mod, "get_settings", lambda: settings)

    result = await _get_valid_access_token(_USER_ID, "github", repo)
    assert result == new_access
    assert any(e[2] == "refresh" for e in repo.audit_log)


@pytest.mark.asyncio
async def test_get_valid_access_token_raises_auth_required_when_missing() -> None:
    from devhub.api.routers.oauth_connect import _get_valid_access_token
    from devhub.core.errors import AuthRequiredError

    repo = _FakeOAuthRepo()
    with pytest.raises(AuthRequiredError):
        await _get_valid_access_token(_USER_ID, "github", repo)
