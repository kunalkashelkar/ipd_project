# ============================================================
# Source Validator — Path Traversal, Binary, and Noise Filtering
# ============================================================

from __future__ import annotations

import os
from pathlib import Path

# Directories to exclude from deep analysis while retaining provenance in manifest
EXCLUDED_DIRECTORIES = {
    "node_modules",
    ".git",
    "vendor",
    "build",
    "dist",
    "target",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}

# File extensions to exclude from code parsing
EXCLUDED_EXTENSIONS = {
    ".min.js",
    ".min.css",
    ".map",
    ".lock",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".class",
    ".jar",
    ".war",
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
}


def sanitize_relative_path(path: str) -> str:
    """Validate and normalize a relative path.

    Raises ValueError if path attempts directory traversal or is absolute.
    """
    clean = path.replace("\\", "/").strip()
    if clean.startswith("/"):
        raise ValueError(f"Absolute path rejected: {path}")

    parts = clean.split("/")

    if any(p == ".." for p in parts):
        raise ValueError(f"Directory traversal detected in path: {path}")

    # Check for Windows drive letter
    if len(parts) > 0 and ":" in parts[0]:
        raise ValueError(f"Windows absolute path detected: {path}")

    normalized = "/".join(p for p in parts if p and p != ".")
    if not normalized:
        raise ValueError("Path resolved to empty string")

    return normalized


def is_binary_content(sample_bytes: bytes) -> bool:
    """Detect whether a file is binary by checking for null bytes and byte decoding."""
    if not sample_bytes:
        return False
    # Check first 8KB for null byte
    chunk = sample_bytes[:8192]
    if b"\x00" in chunk:
        return True
    try:
        chunk.decode("utf-8")
        return False
    except UnicodeDecodeError:
        try:
            chunk.decode("latin-1")
            return False
        except Exception:
            return True


def classify_file(
    relative_path: str, size_bytes: int, is_binary: bool
) -> tuple[str, bool]:
    """Classify file validation status.

    Returns:
        (validation_status, is_excluded)
        validation_status: 'valid' | 'excluded' | 'unsupported' | 'corrupt'
    """
    parts = relative_path.split("/")
    filename = parts[-1].lower()

    # Check directory exclusion
    for part in parts[:-1]:
        if part.lower() in EXCLUDED_DIRECTORIES:
            return "excluded", True

    # Check binary status
    if is_binary:
        return "excluded", True

    # Check extension exclusion
    for ext in EXCLUDED_EXTENSIONS:
        if filename.endswith(ext):
            return "excluded", True

    # Files larger than 5MB are excluded from in-memory parsing
    if size_bytes > 5 * 1024 * 1024:
        return "excluded", True

    return "valid", False


def validate_archive_entry(entry_name: str) -> tuple[str, bool, str]:
    """Validate archive entry for zip-slip, absolute path, and traversal protection."""
    try:
        sanitized = sanitize_relative_path(entry_name)
        return sanitized, True, "Safe path"
    except ValueError as e:
        return entry_name, False, str(e)


def validate_source_file(relative_path: str, content: bytes) -> tuple[bool, str, bool]:
    """Validate source file content and classify type."""
    is_bin = is_binary_content(content)
    if is_bin:
        return True, "binary", True
    val_status, is_exc = classify_file(relative_path, len(content), False)
    classification = "noise" if is_exc else "source"
    return True, classification, False

