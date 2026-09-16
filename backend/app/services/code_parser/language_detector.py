# ============================================================
# Language Detector — Extension & Heuristic Language Detection
# ============================================================

from __future__ import annotations

import re
from pathlib import Path

# Supported languages for Phase 3
SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".pyw": "python",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".php": "php",
}

HEURISTIC_PATTERNS = {
    "python": [re.compile(r"^#!\s*\/.*python"), re.compile(r"\bdef\s+\w+\s*\(.*?\):"), re.compile(r"\bimport\s+\w+")],
    "c": [re.compile(r"#include\s*<stdio\.h>"), re.compile(r"\bint\s+main\s*\(")],
    "cpp": [re.compile(r"#include\s*<iostream>"), re.compile(r"\busing\s+namespace\s+std;"), re.compile(r"\bclass\s+\w+\s*\{")],
    "java": [re.compile(r"\bpublic\s+class\s+\w+"), re.compile(r"\bpackage\s+[\w\.]+;"), re.compile(r"\bpublic\s+static\s+void\s+main")],
    "javascript": [re.compile(r"\bfunction\s+\w+\s*\("), re.compile(r"\bconst\s+\w+\s*=\s*\("), re.compile(r"\bmodule\.exports\b")],
    "typescript": [re.compile(r"\binterface\s+\w+\s*\{"), re.compile(r"\btype\s+\w+\s*="), re.compile(r":\s*(string|number|boolean|any)\b")],
    "go": [re.compile(r"\bpackage\s+\w+"), re.compile(r"\bfunc\s+\w+\s*\("), re.compile(r"\bimport\s*\(")],
    "rust": [re.compile(r"\bfn\s+main\s*\("), re.compile(r"\blet\s+mut\s+"), re.compile(r"\bimpl\s+\w+")],
    "csharp": [re.compile(r"\bnamespace\s+[\w\.]+"), re.compile(r"\busing\s+System;"), re.compile(r"\bpublic\s+class\s+\w+")],
    "php": [re.compile(r"^<\?php"), re.compile(r"\bfunction\s+\w+\s*\("), re.compile(r"\$\w+\s*=")],
}


def detect_file_language(relative_path: str, sample_content: str | bytes | None = None) -> str | None:
    """Detect the programming language using extension and safe content heuristics."""
    if isinstance(sample_content, bytes):
        sample_content = sample_content.decode("utf-8", errors="ignore")

    p = Path(relative_path)
    ext = p.suffix.lower()

    if ext in SUPPORTED_EXTENSIONS:
        lang = SUPPORTED_EXTENSIONS[ext]
        # Disambiguate .h between C and C++ using content heuristics if content is available
        if ext == ".h" and sample_content:
            if "class " in sample_content or "template<" in sample_content or "std::" in sample_content:
                return "cpp"
        return lang

    # Fallback to content heuristics if content is provided
    if sample_content:
        for lang, patterns in HEURISTIC_PATTERNS.items():
            if any(pat.search(sample_content) for pat in patterns):
                return lang

    return None


detect_language = detect_file_language
