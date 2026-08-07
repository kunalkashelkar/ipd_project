# ============================================================
# Hashing Utilities
# ============================================================

from __future__ import annotations

import hashlib


def compute_sha256(content: bytes) -> str:
    """Compute the SHA-256 hash of a byte string."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()
