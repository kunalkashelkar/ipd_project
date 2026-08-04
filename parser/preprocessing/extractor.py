# ============================================================
# Preprocessing — ZIP Extractor
# ============================================================
# Handles decompression of uploaded archives and path normalisation.
# Includes security checks against path-traversal attacks.
# ============================================================

from __future__ import annotations

import zipfile
from pathlib import Path

from loguru import logger


class ExtractionError(Exception):
    """Raised when archive extraction fails."""


class ZIPExtractor:
    """Safely extracts ZIP archives to a target workspace directory."""

    # Maximum allowed uncompressed size (500 MB)
    MAX_UNCOMPRESSED_BYTES: int = 500 * 1024 * 1024

    def extract(self, archive: Path, workspace: Path) -> Path:
        """Extract *archive* under *workspace* and return the root extracted dir.

        Args:
            archive:   Path to the uploaded .zip file.
            workspace: Parent directory under which extraction happens.

        Returns:
            Path to the extracted project root directory.

        Raises:
            ExtractionError: For corrupt archives, path traversal, or size violations.
        """
        if not archive.exists():
            raise ExtractionError(f"Archive not found: {archive}")
        if not zipfile.is_zipfile(archive):
            raise ExtractionError(f"File is not a valid ZIP archive: {archive.name}")

        # Workspace per archive — avoids collisions
        dest = workspace / archive.stem
        dest.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive, "r") as zf:
            self._check_members(zf, dest)
            zf.extractall(dest)

        logger.info(
            "Archive extracted — source={src} dest={dest}",
            src=archive.name,
            dest=dest,
        )
        return dest

    # ── Private helpers ────────────────────────────────────

    def _check_members(self, zf: zipfile.ZipFile, dest: Path) -> None:
        """Validate each ZIP member for path-traversal and size limits."""
        total_size = 0
        dest_resolved = dest.resolve()

        for info in zf.infolist():
            # Security: prevent zip-slip (path traversal attacks)
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest_resolved)):
                raise ExtractionError(
                    f"Path traversal detected in archive member: '{info.filename}'"
                )

            # Size bomb check
            total_size += info.file_size
            if total_size > self.MAX_UNCOMPRESSED_BYTES:
                raise ExtractionError(
                    f"Archive uncompressed size exceeds {self.MAX_UNCOMPRESSED_BYTES // 1024 // 1024} MB limit."
                )


class SingleFileHandler:
    """Handles single uploaded .c/.cpp files (wraps them in a temp directory)."""

    def wrap(self, source_file: Path, workspace: Path) -> Path:
        """Copy a single file into its own subdirectory so downstream code is uniform.

        Args:
            source_file: Path to the uploaded .c or .cpp file.
            workspace:   Parent workspace directory.

        Returns:
            Path to the new directory containing the single file.
        """
        project_dir = workspace / source_file.stem
        project_dir.mkdir(parents=True, exist_ok=True)
        dest = project_dir / source_file.name
        dest.write_bytes(source_file.read_bytes())
        logger.info(
            "Single file wrapped — file={f} dir={d}",
            f=source_file.name,
            d=project_dir,
        )
        return project_dir
