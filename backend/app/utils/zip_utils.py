# ============================================================
# ZIP Utilities — Hardened Archive Extraction & Zip-Slip Defense
# ============================================================

from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.exceptions import ValidationError


def safe_extract_zip(
    zip_source: Path | str | bytes | io.BytesIO,
    extract_to: Path,
    max_size: int | None = None,
    max_files: int | None = None,
) -> None:
    """Safely extract a ZIP archive protecting against Zip-Slip, zip-bombs, and symlink attacks.

    Supports file paths (Path, str), raw binary data (bytes), or BytesIO objects.

    Guarantees:
    1. Every extracted entry strictly resides inside `extract_to`.
    2. Path traversal characters ('..', absolute paths, Windows drive specifiers, UNC paths) are rejected.
    3. Symlinks and hardlinks pointing outside the extraction root are rejected.
    4. Uncompressed size and file count limits are strictly enforced.
    """
    settings = get_settings()
    max_uncompressed_bytes = max_size or getattr(settings, "max_extraction_size_bytes", 500 * 1024 * 1024)
    max_entry_count = max_files or getattr(settings, "max_archive_files", 10000)

    if isinstance(zip_source, bytes):
        zip_obj: Path | io.BytesIO = io.BytesIO(zip_source)
    elif isinstance(zip_source, str):
        zip_obj = Path(zip_source)
    else:
        zip_obj = zip_source

    if not zipfile.is_zipfile(zip_obj):
        raise ValidationError("Invalid or corrupt ZIP file")

    if isinstance(zip_obj, io.BytesIO):
        zip_obj.seek(0)

    extract_to_resolved = extract_to.resolve()
    extract_to_resolved.mkdir(parents=True, exist_ok=True)

    total_size = 0
    file_count = 0

    with zipfile.ZipFile(zip_obj, "r") as zf:
        infolist = zf.infolist()

        if len(infolist) > max_entry_count:
            raise ValidationError(
                f"Archive entry count ({len(infolist)}) exceeds limit ({max_entry_count})"
            )

        for info in infolist:
            file_count += 1
            filename = info.filename

            # 1. Normalize and check filename for suspicious characters
            normalized_name = filename.replace("\\", "/")

            # Reject empty member names
            if not normalized_name or normalized_name == "/":
                continue

            # Reject drive letters (e.g. C:, D:) and UNC paths (//server/share)
            if ":" in normalized_name or normalized_name.startswith("//"):
                raise ValidationError(f"Suspicious path in ZIP archive: {filename}")

            # Reject leading slashes or explicit parent references
            parts = normalized_name.split("/")
            if ".." in parts or normalized_name.startswith("/"):
                raise ValidationError(f"Path traversal detected in ZIP archive: {filename}")

            # 2. Check for symlinks in ZIP attributes
            # In Unix, standard zip symlink mode has S_IFLNK (0o120000)
            mode = info.external_attr >> 16
            if mode & 0o170000 == 0o120000:
                raise ValidationError(f"Symlinks inside archive are not permitted: {filename}")

            # 3. Check for zip bomb (accumulated uncompressed size)
            total_size += info.file_size
            if total_size > max_uncompressed_bytes:
                raise ValidationError(
                    f"ZIP archive exceeds maximum uncompressed size limit ({max_uncompressed_bytes} bytes)"
                )

            # 4. Resolve destination path and verify strict containment
            dest_path = (extract_to_resolved / normalized_name).resolve()
            try:
                dest_path.relative_to(extract_to_resolved)
            except ValueError as exc:
                raise ValidationError(
                    f"Entry escapes extraction directory: {filename}"
                ) from exc

            # 5. Extract safely
            if info.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src_file, open(dest_path, "wb") as dst_file:
                    # Stream copy in chunks to prevent memory exhaustion
                    while chunk := src_file.read(65536):
                        dst_file.write(chunk)
