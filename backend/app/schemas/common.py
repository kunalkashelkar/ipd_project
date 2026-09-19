# ============================================================
# Common Schemas — Response envelope, pagination, enums
# ============================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ── Response Envelope ──────────────────────────────────────


class ErrorDetail(BaseModel):
    """Single field-level error detail."""

    field: str | None = None
    message: str


class APIResponse(BaseModel):
    """Standardized API response envelope."""

    status: str = "success"
    message: str = ""
    data: Any = None
    errors: list[ErrorDetail] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginatedData(BaseModel, Generic[T]):
    """Paginated data wrapper."""

    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


# ── Pagination Query Params ────────────────────────────────


class PaginationParams(BaseModel):
    """Query parameters for pagination."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order: asc or desc")
    search: str | None = Field(default=None, description="Search query")


# ── Health ─────────────────────────────────────────────────


class HealthData(BaseModel):
    """Health check data."""

    app: str = "VulnScan"
    version: str = "0.1.0"
    environment: str = "development"
    database: str = "unknown"
    redis: str = "unknown"
