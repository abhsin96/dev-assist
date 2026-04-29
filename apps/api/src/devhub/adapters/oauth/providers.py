"""OAuth provider clients for GitHub and Slack.

Each provider exposes:
  - ``build_auth_url``  — construct the consent-screen redirect URL
  - ``exchange_code``   — POST code → tokens
  - ``refresh_tokens``  — POST refresh_token → new tokens
  - ``revoke_token``    — invalidate at provider

Design invariant: raw tokens never appear in exception messages or log context.
All errors carry only status codes and provider error codes, not token values.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

import httpx

from devhub.core.errors import UpstreamError
from devhub.core.settings import Settings
from devhub.domain.models import OAuthProvider

_GITHUB_SCOPES = "repo read:user"
_SLACK_SCOPES = "channels:history channels:read chat:write"


@dataclass(frozen=True, slots=True)
class OAuthTokens:
    access_token: str
    refresh_token: str | None
    scope: str
    expires_in: int | None  # seconds; None = non-expiring (GitHub)


# ── URL construction ──────────────────────────────────────────────────────────


def build_auth_url(
    provider: OAuthProvider,
    state: str,
    redirect_uri: str,
    settings: Settings,
) -> str:
    if provider == "github":
        params = {
            "client_id": settings.github_client_id,
            "scope": _GITHUB_SCOPES,
            "state": state,
            "redirect_uri": redirect_uri,
        }
        return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)
    else:
        params = {
            "client_id": settings.slack_client_id,
            "scope": _SLACK_SCOPES,
            "state": state,
            "redirect_uri": redirect_uri,
        }
        return "https://slack.com/oauth/v2/authorize?" + urllib.parse.urlencode(params)


# ── Token exchange ────────────────────────────────────────────────────────────


async def exchange_code(
    provider: OAuthProvider,
    code: str,
    redirect_uri: str,
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> OAuthTokens:
    owned = http_client is None
    client = http_client or httpx.AsyncClient()
    try:
        if provider == "github":
            return await _github_exchange(client, code, redirect_uri, settings)
        return await _slack_exchange(client, code, redirect_uri, settings)
    finally:
        if owned:
            await client.aclose()


async def _github_exchange(
    client: httpx.AsyncClient,
    code: str,
    redirect_uri: str,
    settings: Settings,
) -> OAuthTokens:
    resp = await client.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
    )
    if resp.status_code != 200:
        raise UpstreamError(f"GitHub token exchange failed: {resp.status_code}")
    data = resp.json()
    if "error" in data:
        raise UpstreamError(f"GitHub token exchange error: {data['error']}")
    return OAuthTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope", _GITHUB_SCOPES),
        expires_in=data.get("expires_in"),
    )


async def _slack_exchange(
    client: httpx.AsyncClient,
    code: str,
    redirect_uri: str,
    settings: Settings,
) -> OAuthTokens:
    resp = await client.post(
        "https://slack.com/api/oauth.v2.access",
        data={"code": code, "redirect_uri": redirect_uri},
        auth=(settings.slack_client_id, settings.slack_client_secret),
    )
    if resp.status_code != 200:
        raise UpstreamError(f"Slack token exchange failed: {resp.status_code}")
    data = resp.json()
    if not data.get("ok"):
        raise UpstreamError(f"Slack token exchange error: {data.get('error', 'unknown')}")
    return OAuthTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope", _SLACK_SCOPES),
        expires_in=data.get("expires_in"),
    )


# ── Token refresh ─────────────────────────────────────────────────────────────


async def refresh_tokens(
    provider: OAuthProvider,
    refresh_token: str,
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> OAuthTokens:
    owned = http_client is None
    client = http_client or httpx.AsyncClient()
    try:
        if provider == "github":
            return await _github_refresh(client, refresh_token, settings)
        return await _slack_refresh(client, refresh_token, settings)
    finally:
        if owned:
            await client.aclose()


async def _github_refresh(
    client: httpx.AsyncClient,
    refresh_token: str,
    settings: Settings,
) -> OAuthTokens:
    resp = await client.post(
        "https://github.com/login/oauth/access_token",
        json={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        headers={"Accept": "application/json"},
    )
    if resp.status_code != 200:
        raise UpstreamError(f"GitHub token refresh failed: {resp.status_code}")
    data = resp.json()
    if "error" in data:
        raise UpstreamError(f"GitHub token refresh error: {data['error']}")
    return OAuthTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope", _GITHUB_SCOPES),
        expires_in=data.get("expires_in"),
    )


async def _slack_refresh(
    client: httpx.AsyncClient,
    refresh_token: str,
    settings: Settings,
) -> OAuthTokens:
    resp = await client.post(
        "https://slack.com/api/oauth.v2.exchange",
        data={"refresh_token": refresh_token, "grant_type": "refresh_token"},
        auth=(settings.slack_client_id, settings.slack_client_secret),
    )
    if resp.status_code != 200:
        raise UpstreamError(f"Slack token refresh failed: {resp.status_code}")
    data = resp.json()
    if not data.get("ok"):
        raise UpstreamError(f"Slack token refresh error: {data.get('error', 'unknown')}")
    return OAuthTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        scope=data.get("scope", _SLACK_SCOPES),
        expires_in=data.get("expires_in"),
    )


# ── Revocation ────────────────────────────────────────────────────────────────


async def revoke_token(
    provider: OAuthProvider,
    access_token: str,
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    owned = http_client is None
    client = http_client or httpx.AsyncClient()
    try:
        if provider == "github":
            await _github_revoke(client, access_token, settings)
        else:
            await _slack_revoke(client, access_token, settings)
    finally:
        if owned:
            await client.aclose()


async def _github_revoke(
    client: httpx.AsyncClient,
    access_token: str,
    settings: Settings,
) -> None:
    resp = await client.request(
        "DELETE",
        f"https://api.github.com/applications/{settings.github_client_id}/token",
        json={"access_token": access_token},
        auth=(settings.github_client_id, settings.github_client_secret),
        headers={"Accept": "application/vnd.github+json"},
    )
    if resp.status_code not in (204, 422):
        raise UpstreamError(f"GitHub revoke failed: {resp.status_code}")


async def _slack_revoke(
    client: httpx.AsyncClient,
    access_token: str,
    settings: Settings,  # noqa: ARG001
) -> None:
    resp = await client.post(
        "https://slack.com/api/auth.revoke",
        data={"token": access_token},
    )
    if resp.status_code != 200:
        raise UpstreamError(f"Slack revoke failed: {resp.status_code}")
    data = resp.json()
    if not data.get("ok") and data.get("error") != "token_revoked":
        raise UpstreamError(f"Slack revoke error: {data.get('error', 'unknown')}")
