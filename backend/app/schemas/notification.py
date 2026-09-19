# ============================================================
# Notification Schemas (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Notification response with Phase 7 fields."""

    id: uuid.UUID
    public_id: str | None = None
    user_id: uuid.UUID
    organization_id: uuid.UUID | None = None
    type: str
    title: str
    body: str | None = None
    severity: str = "info"
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    link_url: str | None = None
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Unread notification count."""

    count: int = 0
