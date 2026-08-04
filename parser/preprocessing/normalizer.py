# ============================================================
# Preprocessing — File Normalizer
# ============================================================
# Lightweight cleanup of source files before Joern parsing.
# Handles line endings, BOM markers, and trailing whitespace.
# ============================================================

from __future__ import annotations

from pathlib import Path

from loguru import logger


class Normalizer:
    """Cleans up source file encoding issues in-place before parsing."""

    def normalize_project(self, root: Path, source_files: list[Path]) -> int:
        """Normalize all source files in the project.

        Args:
            root:         Project root (for logging context).
            source_files: List of absolute paths to normalize.

        Returns:
            Number of files that were modified.
        """
        modified = 0
        for f in source_files:
            if self._normalize_file(f):
                modified += 1

        if modified:
            logger.info(
                "Normalized {n}/{total} files in '{root}'",
                n=modified,
                total=len(source_files),
                root=root.name,
            )
        return modified

    # ── Private helpers ────────────────────────────────────

    def _normalize_file(self, path: Path) -> bool:
        """Normalize a single file. Returns True if the file was changed."""
        try:
            raw = path.read_bytes()

            # Decode — try UTF-8, fall back to latin-1 (covers most C source)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")

            cleaned = self._clean_text(text)
            encoded = cleaned.encode("utf-8")

            if encoded != raw:
                path.write_bytes(encoded)
                return True
            return False
        except OSError as e:
            logger.warning("Could not normalize file {p}: {e}", p=path, e=e)
            return False

    def _clean_text(self, text: str) -> str:
        """Apply normalisation rules to *text*."""
        # 1. Remove BOM (byte-order mark)
        text = text.lstrip("\ufeff")

        # 2. Normalise CRLF → LF (Windows line endings)
        text = text.replace("\r\n", "\n")

        # 3. Normalise CR-only → LF (old macOS)
        text = text.replace("\r", "\n")

        # 4. Strip trailing whitespace on each line
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(lines)

        # 5. Ensure single trailing newline
        text = text.rstrip("\n") + "\n"

        return text
