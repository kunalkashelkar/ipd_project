# ============================================================
# Language Detection Utility
# ============================================================

from __future__ import annotations


def detect_language(extension: str) -> str:
    """Detect programming language from file extension."""
    ext = extension.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".cs": "csharp",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
    }
    return mapping.get(ext, "unknown")
