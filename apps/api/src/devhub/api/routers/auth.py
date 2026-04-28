from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from devhub.adapters.persistence.database import get_db
from devhub.adapters.persistence.repositories import UserRepository
from devhub.api.deps import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me")
async def me(
    claims: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    repo = UserRepository(db)
    user = await repo.upsert(
        email=str(claims["sub"]),
        name=claims.get("name") and str(claims["name"]),  # type: ignore[arg-type]
        avatar_url=claims.get("image") and str(claims["image"]),  # type: ignore[arg-type]
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }
