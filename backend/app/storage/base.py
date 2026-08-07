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
        """Get a public or signed URL for the file."""
        pass
