# ============================================================
# Preprocessing — Source File Validator
# ============================================================
# Discovers C/C++ source files in a project directory,
# detects the programming language, and returns project metadata.
# Ignores build artefacts, VCS directories and binaries.
# ============================================================

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

# Directories that are silently skipped during file discovery
_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".svn",
        ".hg",
        "build",
        "cmake-build-debug",
        "cmake-build-release",
        "node_modules",
        "__pycache__",
        ".cache",
        "dist",
        "out",
        ".vscode",
        ".idea",
        "vendor",
        "third_party",
        "deps",
        "external",
    }
)

# Extensions that count as C/C++ source files
_C_EXTENSIONS: frozenset[str] = frozenset({".c", ".h"})
_CPP_EXTENSIONS: frozenset[str] = frozenset({".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx"})
_SOURCE_EXTENSIONS: frozenset[str] = _C_EXTENSIONS | _CPP_EXTENSIONS

# Allowed upload extensions (strict)
ALLOWED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset({".c", ".cpp", ".h", ".hpp", ".zip"})


@dataclass
class ProjectMetadata:
    """Structured metadata returned by the validator."""

    name: str
    root_path: Path
    language: str                          # "C", "C++", or "Mixed"
    source_files: list[Path] = field(default_factory=list)
    file_count: int = 0
    project_size_bytes: int = 0
    content_hash: str = ""                 # SHA-256 over all source file paths+sizes

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "root_path": str(self.root_path),
            "language": self.language,
            "source_files": [str(p) for p in self.source_files],
            "file_count": self.file_count,
            "project_size_bytes": self.project_size_bytes,
            "content_hash": self.content_hash,
        }


class ValidationError(Exception):
    """Raised when a project directory is invalid or unacceptable."""


class ProjectValidator:
    """Validates and inventories a C/C++ project directory."""

    def validate(self, root: Path) -> ProjectMetadata:
        """Validate *root* and return structured project metadata.

        Args:
            root: Path to the extracted project directory.

        Returns:
            ProjectMetadata with all discovered source files.

        Raises:
            ValidationError: If the path is invalid or no source files are found.
        """
        if not root.exists():
            raise ValidationError(f"Project path does not exist: {root}")
        if not root.is_dir():
            raise ValidationError(f"Project path is not a directory: {root}")

        source_files = self._discover_files(root)

        if not source_files:
            raise ValidationError(
                f"No C/C++ source files found under '{root}'. "
                "Ensure the archive contains .c, .cpp, .h, or .hpp files."
            )

        language = self._detect_language(source_files)
        size = sum(f.stat().st_size for f in source_files)
        content_hash = self._compute_project_hash(source_files)

        logger.info(
            "Project validated — name={name} files={n} language={lang} size={size}B",
            name=root.name,
            n=len(source_files),
            lang=language,
            size=size,
        )

        return ProjectMetadata(
            name=root.name,
            root_path=root,
            language=language,
            source_files=source_files,
            file_count=len(source_files),
            project_size_bytes=size,
            content_hash=content_hash,
        )

    # ── Private helpers ────────────────────────────────────

    def _discover_files(self, root: Path) -> list[Path]:
        """Walk the directory tree and collect source files."""
        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune ignored directories in-place (modifies os.walk)
            dirnames[:] = [
                d for d in dirnames if d not in _IGNORE_DIRS and not d.startswith(".")
            ]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in _SOURCE_EXTENSIONS:
                    files.append(Path(dirpath) / fname)
        return sorted(files)

    def _detect_language(self, files: list[Path]) -> str:
        """Determine if the project is C, C++, or mixed."""
        has_c = any(f.suffix.lower() in _C_EXTENSIONS for f in files)
        has_cpp = any(f.suffix.lower() in _CPP_EXTENSIONS for f in files)
        if has_c and has_cpp:
            return "Mixed"
        if has_cpp:
            return "C++"
        return "C"

    def _compute_project_hash(self, files: list[Path]) -> str:
        """SHA-256 fingerprint over relative file paths and sizes (cheap, not content)."""
        h = hashlib.sha256()
        for f in files:
            h.update(f.name.encode())
            h.update(str(f.stat().st_size).encode())
        return h.hexdigest()


def validate_upload_extension(filename: str) -> str:
    """Return the lowercased extension or raise ValidationError."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f"Extension '{ext}' is not allowed. "
            f"Accepted: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}"
        )
    return ext
