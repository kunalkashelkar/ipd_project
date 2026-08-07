# ============================================================
# Standardized API Response Envelope
# ============================================================
# All endpoints return responses through these helpers.
# Structure: {status, message, data, errors, timestamp}
# ============================================================

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


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


def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = 200,
) -> dict:
    """Build a success response dict.

    Use as: ``return success_response(data={...}, message="Created")``
    """
    return {
        "status": "success",
        "message": message,
        "data": data,
        "errors": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def error_response(
    message: str = "An error occurred",
    errors: list[dict] | None = None,
    status_code: int = 400,
) -> dict:
    """Build an error response dict.

    ``errors`` should be a list of ``{"field": ..., "message": ...}`` dicts.
    """
    return {
        "status": "error",
        "message": message,
        "data": None,
        "errors": errors or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def paginated_response(
    items: list[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "Success",
) -> dict:
    """Build a paginated success response."""
    return {
        "status": "success",
        "message": message,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0,
        },
        "errors": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
