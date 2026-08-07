# ============================================================
# Notification Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response."""

    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Unread notification count."""

    count: int = 0
