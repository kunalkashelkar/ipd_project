# ============================================================
# Application Configuration — Backward Compatibility Proxy
# ============================================================
# This module re-exports Settings and get_settings from
# backend.app.core.config to ensure a single, unified source of truth.
# ============================================================

from backend.app.core.config import PROJECT_ROOT, BACKEND_ROOT, Settings, get_settings

__all__ = ["PROJECT_ROOT", "BACKEND_ROOT", "Settings", "get_settings"]
