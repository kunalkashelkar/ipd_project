# ============================================================
# User Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """Public user data."""

    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    active_organization_role: str | None = None
    status: str
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User profile update."""

    name: str | None = None
    email: EmailStr | None = None


class UserAdminUpdate(BaseModel):
    """Admin-only user update."""

    name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    status: str | None = None
