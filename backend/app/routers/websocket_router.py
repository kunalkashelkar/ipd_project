# ============================================================
# WebSocket Router
# ============================================================

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.core.security import decode_token
from backend.app.websocket.manager import manager
from backend.app.core.logging import logger

router = APIRouter(tags=["WebSockets"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket connection endpoint.

    Requires a valid JWT token passed as a query parameter.
    """
    try:
        # Validate token
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return
    except Exception as exc:
        logger.warning("WebSocket authentication failed: {exc}", exc=str(exc))
        await websocket.close(code=1008)
        return

    # Connect
    await manager.connect(websocket, user_id)

    try:
        while True:
            # Keep connection alive and handle client messages if needed
            data = await websocket.receive_text()
            # For now, we only push data to clients, so we ignore client messages
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
