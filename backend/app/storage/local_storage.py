# ============================================================
# Local Storage Backend — Path Traversal Hardened
# ============================================================

from __future__ import annotations

import os
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.exceptions import StorageError
from backend.app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Stores files on the local filesystem with strict path containment checks."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = (base_dir or get_settings().storage_path).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve a relative path and guarantee it remains inside base_dir."""
        # Sanitize Windows drive letters, backslashes, leading slashes
        clean_path = relative_path.replace("\\", "/").lstrip("/")
        if ".." in clean_path.split("/"):
            raise StorageError("Path traversal detected in storage path")

        target = (self.base_dir / clean_path).resolve()
        try:
            target.relative_to(self.base_dir)
        except ValueError as exc:
            raise StorageError(f"Target path escapes storage root: {relative_path}") from exc

        return target

    async def store(self, content: bytes, path: str) -> str:
        """Store content to local disk inside the base storage directory."""
        target = self._resolve_safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(content)
            # Return path relative to base_dir or absolute string
            return str(target)
        except OSError as exc:
            raise StorageError(f"Failed to store file: {exc}") from exc

    async def retrieve(self, path: str) -> bytes:
        """Read content from local disk, verifying storage boundary."""
        # Check if path is absolute or relative
        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
            try:
                resolved.relative_to(self.base_dir)
            except ValueError as exc:
                raise StorageError("Access outside storage boundary is forbidden") from exc
            target = resolved
        else:
            target = self._resolve_safe_path(path)

        if not target.exists() or not target.is_file():
            raise StorageError(f"File not found: {path}")

        try:
            return target.read_bytes()
        except OSError as exc:
            raise StorageError(f"Failed to read file: {exc}") from exc

    async def delete(self, path: str) -> bool:
        """Delete file from local disk inside storage boundary."""
        p = Path(path)
        if p.is_absolute():
            resolved = p.resolve()
            try:
                resolved.relative_to(self.base_dir)
            except ValueError:
                return False
            target = resolved
        else:
            target = self._resolve_safe_path(path)

        if target.exists() and target.is_file():
            try:
                target.unlink()
                # Clean up empty parent directories up to base_dir
                parent = target.parent
                while parent != self.base_dir and parent.exists():
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break
                return True
            except OSError as exc:
                raise StorageError(f"Failed to delete file: {exc}") from exc
        return False

    async def get_url(self, path: str) -> str:
        """Return a local file URI."""
        p = Path(path)
        if p.is_absolute():
            target = p.resolve()
        else:
            target = self._resolve_safe_path(path)
        return f"file://{target.as_posix()}"

    async def object_exists(self, path: str) -> bool:
        """Check if an object exists on local disk."""
        try:
            p = Path(path)
            target = p.resolve() if p.is_absolute() else self._resolve_safe_path(path)
            return target.is_file()
        except Exception:
            return False

    async def head_object(self, path: str) -> dict | None:
        """Retrieve file stats on local disk."""
        try:
            p = Path(path)
            target = p.resolve() if p.is_absolute() else self._resolve_safe_path(path)
            if not target.is_file():
                return None
            stat = target.stat()
            return {
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            }
        except Exception:
            return None

    async def copy_object(self, source_path: str, dest_path: str) -> str:
        """Copy local file to target path."""
        content = await self.retrieve(source_path)
        return await self.store(content, dest_path)

    async def generate_download_reference(self, path: str, expires_in_seconds: int = 3600) -> str:
        """Return local URL."""
        return await self.get_url(path)
