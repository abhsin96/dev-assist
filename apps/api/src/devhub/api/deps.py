from __future__ import annotations

from typing import Annotated

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from devhub.adapters.auth.jwt import decode_api_token
from devhub.core.errors import AuthError

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
) -> dict[str, object]:
    if not credentials:
        raise AuthError("Authentication required")
    return decode_api_token(credentials.credentials)


CurrentUser = Annotated[dict[str, object], Security(get_current_user)]
