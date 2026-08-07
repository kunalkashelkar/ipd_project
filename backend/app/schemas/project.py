# ============================================================
# Project Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Create a new project."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    language: str | None = None
    default_branch: str | None = "main"


class ProjectUpdate(BaseModel):
    """Update an existing project."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    language: str | None = None
    default_branch: str | None = None
    is_archived: bool | None = None


class ProjectResponse(BaseModel):
    """Project response data."""

    id: uuid.UUID
    name: str
    description: str | None = None
    language: str | None = None
    default_branch: str | None = None
    owner_id: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
