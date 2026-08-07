# ============================================================
# WebSocket Events
# ============================================================

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WSEvent(BaseModel):
    """Base schema for WebSocket events."""

    type: str
    payload: dict[str, Any]


def create_scan_update_event(scan_id: str, status: str, progress: float) -> WSEvent:
    """Create an event for scan progress updates."""
    return WSEvent(
        type="scan_update",
        payload={
            "scan_id": scan_id,
            "status": status,
            "progress": progress,
        },
    )


def create_notification_event(notification_id: str, title: str, message: str) -> WSEvent:
    """Create an event for a new notification."""
    return WSEvent(
        type="notification",
        payload={
            "id": notification_id,
            "title": title,
            "message": message,
        },
    )
