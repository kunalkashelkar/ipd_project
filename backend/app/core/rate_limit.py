# ============================================================
# Rate Limiting Engine — Redis Sliding Window + In-Memory Fallback
# ============================================================
# Provides bounded request rate enforcement for security-critical
# endpoints (auth, scans, reports, uploads, webhooks).
# Employs Redis sorted sets when available with seamless in-memory
# fallback during local development or transient Redis disconnects.
# ============================================================

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import Request
import redis.asyncio as aioredis

from backend.app.core.config import get_settings
from backend.app.core.exceptions import RateLimitExceededError
from backend.app.core.logging import logger

# In-memory fallback tracking: { "scope:key": [timestamps] }
_in_memory_windows: dict[str, list[float]] = defaultdict(list)
_in_memory_lock = asyncio.Lock()


def default_identifier(request: Request) -> str:
    """Derive rate-limiting identifier from request.
    
    Prefers authenticated user/tenant ID, falling back to client IP.
    """
    # Check for authenticated user from auth dependency / state
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"usr_{user.id}"

    # Check for authorization header bearer token snippet
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if len(token) > 16:
            return f"tok_{token[-16:]}"

    # Fallback to client host IP
    client = request.client
    if client and client.host:
        return f"ip_{client.host}"

    return "anonymous"


class RateLimiter:
    """FastAPI dependency for bounded sliding-window rate limiting."""

    def __init__(
        self,
        times: int,
        seconds: int,
        scope: str = "default",
        key_func: Callable[[Request], str] | None = None,
    ):
        self.times = times
        self.seconds = seconds
        self.scope = scope
        self.key_func = key_func or default_identifier

    async def __call__(self, request: Request) -> None:
        settings = get_settings()

        # Check if rate limiting is globally disabled in configuration
        if not getattr(settings, "rate_limiting_enabled", True):
            return

        identifier = self.key_func(request)
        rate_key = f"rl:{self.scope}:{identifier}"
        now = time.time()
        window_start = now - self.seconds

        # Attempt Redis sliding window
        redis_client = None
        try:
            redis_client = aioredis.from_url(
                settings.redis_url,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
            pipe = redis_client.pipeline(transaction=True)
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zcard(rate_key)
            pipe.zadd(rate_key, {f"{now}:{uuid.uuid4().hex[:6]}": now})
            pipe.expire(rate_key, self.seconds + 2)
            results = await pipe.execute()

            current_count = results[1]  # count before this request was added
            if current_count >= self.times:
                retry_after = max(1, int(self.seconds))
                logger.warning(
                    "Rate limit exceeded (Redis) for scope={scope} key={key} ({count}/{times})",
                    scope=self.scope,
                    key=rate_key,
                    count=current_count + 1,
                    times=self.times,
                )
                raise RateLimitExceededError(
                    message=f"Rate limit exceeded for {self.scope}. Try again in {retry_after} seconds.",
                    retry_after=retry_after,
                )
            return
        except RateLimitExceededError:
            raise
        except Exception as exc:
            # Redis is unreachable or degraded — fall back to in-memory sliding window
            logger.debug(
                "Redis unavailable for rate-limiting, falling back to in-memory tracker: {exc}",
                exc=str(exc),
            )
        finally:
            if redis_client is not None:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

        # In-Memory fallback implementation
        async with _in_memory_lock:
            timestamps = _in_memory_windows[rate_key]
            # Prune old timestamps
            valid_timestamps = [t for t in timestamps if t > window_start]
            if len(valid_timestamps) >= self.times:
                oldest = valid_timestamps[0]
                retry_after = max(1, int(self.seconds - (now - oldest)))
                logger.warning(
                    "Rate limit exceeded (In-Memory) for scope={scope} key={key} ({count}/{times})",
                    scope=self.scope,
                    key=rate_key,
                    count=len(valid_timestamps) + 1,
                    times=self.times,
                )
                raise RateLimitExceededError(
                    message=f"Rate limit exceeded for {self.scope}. Try again in {retry_after} seconds.",
                    retry_after=retry_after,
                )

            valid_timestamps.append(now)
            _in_memory_windows[rate_key] = valid_timestamps
