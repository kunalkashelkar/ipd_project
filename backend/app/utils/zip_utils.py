# ============================================================
# ZIP Utilities
# ============================================================

from __future__ import annotations

import zipfile
from pathlib import Path

from backend.app.core.exceptions import ValidationError


def safe_extract_zip(zip_path: Path, extract_to: Path, max_size: int = 1024 * 1024 * 500) -> None:
    """Safely extract a ZIP file to prevent zip-bombs and path traversal."""
    if not zipfile.is_zipfile(zip_path):
        raise ValidationError("Invalid ZIP file")

    total_size = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            # Check for path traversal (Zip-Slip)
            if ".." in info.filename or info.filename.startswith("/"):
                raise ValidationError(f"Invalid path in ZIP archive: {info.filename}")

            # Check for zip bomb (size limit)
            total_size += info.file_size
            if total_size > max_size:
                raise ValidationError("ZIP archive exceeds maximum uncompressed size limit")

            zf.extract(info, extract_to)
