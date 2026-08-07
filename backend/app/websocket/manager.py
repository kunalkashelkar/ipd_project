# ============================================================
# WebSocket Connection Manager
# ============================================================

from __future__ import annotations

from typing import Dict, List

from fastapi import WebSocket

from backend.app.core.logging import logger


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self):
        # Maps user_id to a list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.debug("WebSocket connected for user {user_id}", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a disconnected WebSocket."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.debug("WebSocket disconnected for user {user_id}", user_id=user_id)

    async def send_personal_message(self, message: dict, user_id: str):
        """Send a JSON message to all connections of a specific user."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as exc:
                    logger.warning("Failed to send WS message to user {user_id}: {exc}", user_id=user_id, exc=str(exc))

    async def broadcast(self, message: dict):
        """Send a JSON message to all connected users."""
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()
