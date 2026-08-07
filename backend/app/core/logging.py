# ============================================================
# Structured Logging
# ============================================================
# Uses loguru for structured, JSON-friendly logging.
# Provides request-context fields (request_id, user_id, etc).
# ============================================================

from __future__ import annotations

import sys

from loguru import logger


def setup_logging(log_level: str = "DEBUG", log_dir: str | None = None) -> None:
    """Configure loguru with structured formatting.

    Call once during application startup.
    """
    # Remove default handler
    logger.remove()

    # Console handler — human-readable
    logger.add(
        sys.stderr,
        level=log_level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
        colorize=True,
    )

    # File handler — JSON lines for production log aggregation
    if log_dir:
        from pathlib import Path

        Path(log_dir).mkdir(parents=True, exist_ok=True)
        logger.add(
            f"{log_dir}/app.log",
            level=log_level.upper(),
            rotation="50 MB",
            retention="30 days",
            compression="gz",
            serialize=True,  # JSON lines
        )

    logger.info("Logging configured at level={level}", level=log_level)


__all__ = ["logger", "setup_logging"]
