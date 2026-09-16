# ============================================================
# Storage Interface
# ============================================================

from __future__ import annotations

import abc
from pathlib import Path


class StorageBackend(abc.ABC):
    """Abstract base class for file storage."""

    @abc.abstractmethod
    async def store(self, content: bytes, path: str) -> str:
        """Store content and return the stored URI/path."""
        pass

    @abc.abstractmethod
    async def retrieve(self, path: str) -> bytes:
        """Retrieve content from a URI/path."""
        pass

    @abc.abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete content at a URI/path."""
        pass

    @abc.abstractmethod
    async def get_url(self, path: str) -> str:
        """Get a public or internal reference URL for the file."""
        pass

    @abc.abstractmethod
    async def object_exists(self, path: str) -> bool:
        """Check if an object exists at the given path."""
        pass

    @abc.abstractmethod
    async def head_object(self, path: str) -> dict | None:
        """Retrieve object metadata without downloading content."""
        pass

    @abc.abstractmethod
    async def copy_object(self, source_path: str, dest_path: str) -> str:
        """Copy an object from source path to destination path."""
        pass

    @abc.abstractmethod
    async def generate_download_reference(self, path: str, expires_in_seconds: int = 3600) -> str:
        """Generate a time-limited download URL or access reference."""
        pass
