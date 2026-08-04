# ============================================================
# Structured Logging — Loguru Configuration
# ============================================================
# Provides a pre-configured logger instance for the entire app.
# Logs to both stderr (dev) and rotating files (production).
# ============================================================

from __future__ import annotations

import sys

from loguru import logger

from backend.app.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging using Loguru.

    Call this once during application startup (in main.py lifespan).
    """
    settings = get_settings()

    # Remove default logger to avoid duplicate output
    logger.remove()

    # ── Console output ─────────────────────────────────────
    logger.add(
        sys.stderr,
        level=settings.app_log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=True,
        diagnose=settings.app_debug,
    )

    # ── File output: general application log ───────────────
    log_dir = settings.log_path
    logger.add(
        str(log_dir / "app.log"),
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        enqueue=True,  # thread-safe
    )

    # ── File output: errors only ───────────────────────────
    logger.add(
        str(log_dir / "error.log"),
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        enqueue=True,
    )

    # ── File output: upload events ─────────────────────────
    logger.add(
        str(log_dir / "uploads.log"),
        level="INFO",
        rotation="5 MB",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        filter=lambda record: "upload" in record["extra"].get("category", ""),
        enqueue=True,
    )

    logger.info("Logging configured — level={level}, log_dir={log_dir}", level=settings.app_log_level, log_dir=str(log_dir))


# Re-export logger for convenient imports:
#   from backend.app.utils.logging import logger
__all__ = ["logger", "setup_logging"]
