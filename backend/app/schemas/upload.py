# ============================================================
# Upload Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Upload record response."""

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID | None = None
    original_name: str
    file_type: str
    size_bytes: int
    sha256_hash: str
    file_count: int | None = 0
    language: str | None = None
    status: str
    error_message: str | None = None
    metadata_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
