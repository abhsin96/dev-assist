from __future__ import annotations

from jose import JWTError, jwt

from devhub.core.errors import AuthError
from devhub.core.settings import get_settings


def decode_api_token(token: str) -> dict[str, object]:
    settings = get_settings()
    try:
        payload: dict[str, object] = jwt.decode(
            token, settings.api_jwt_secret, algorithms=["HS256"]
        )
    except JWTError as exc:
        raise AuthError("Invalid or expired token") from exc

    if not payload.get("sub"):
        raise AuthError("Token missing subject claim")

    return payload
