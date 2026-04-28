from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    email: str
    name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class Thread(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


RunStatus = Literal["pending", "running", "completed", "failed"]


class Run(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    thread_id: uuid.UUID
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    error_data: dict[str, Any] | None = None
