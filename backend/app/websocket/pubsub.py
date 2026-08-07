# ============================================================
# Redis PubSub for WebSockets
# ============================================================
# Allows background Celery workers to publish messages to
# FastAPI WebSocket managers across multiple ASGI workers.
# ============================================================

from __future__ import annotations

import asyncio
import json

from loguru import logger
import redis.asyncio as aioredis

from backend.app.core.config import get_settings
from backend.app.websocket.manager import manager


async def redis_listener():
    """Listen for messages on Redis and broadcast via WebSockets."""
    settings = get_settings()
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("ws_messages")

        logger.info("Started Redis PubSub listener for WebSockets")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    user_id = data.get("user_id")
                    payload = data.get("payload")

                    if user_id and payload:
                        await manager.send_personal_message(payload, user_id)
                except Exception as exc:
                    logger.error("Error processing PubSub message: {exc}", exc=str(exc))
    except Exception as exc:
        logger.error("Redis PubSub listener failed: {exc}", exc=str(exc))


async def publish_ws_message(user_id: str, payload: dict):
    """Publish a message to Redis to be picked up by the listener."""
    settings = get_settings()
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        message = json.dumps({"user_id": user_id, "payload": payload})
        await redis_client.publish("ws_messages", message)
        await redis_client.close()
    except Exception as exc:
        logger.error("Failed to publish to Redis: {exc}", exc=str(exc))
