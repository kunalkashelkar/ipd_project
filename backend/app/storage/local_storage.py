# ============================================================
# Local Storage Backend
# ============================================================

from __future__ import annotations

import os
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.exceptions import StorageError
from backend.app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Stores files on the local filesystem."""

    def __init__(self):
        self.base_dir = get_settings().upload_path
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def store(self, content: bytes, path: str) -> str:
        """Store content to local disk."""
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            full_path.write_bytes(content)
            return str(full_path)
        except OSError as exc:
            raise StorageError(f"Failed to store file: {exc}") from exc

    async def retrieve(self, path: str) -> bytes:
        """Read content from local disk."""
        full_path = Path(path)
        if not full_path.exists():
            raise StorageError(f"File not found: {path}")
        try:
            return full_path.read_bytes()
        except OSError as exc:
            raise StorageError(f"Failed to read file: {exc}") from exc

    async def delete(self, path: str) -> bool:
        """Delete file from local disk."""
        full_path = Path(path)
        if full_path.exists():
            try:
                full_path.unlink()
                # Clean up empty parent directories
                parent = full_path.parent
                if parent != self.base_dir and not any(parent.iterdir()):
                    parent.rmdir()
                return True
            except OSError as exc:
                raise StorageError(f"Failed to delete file: {exc}") from exc
        return False

    async def get_url(self, path: str) -> str:
        """Return a local file URI."""
        return f"file://{Path(path).absolute()}"
