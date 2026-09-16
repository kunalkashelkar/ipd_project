# ============================================================
# Identifier Normalizer & Comment Stripper (Derived Representations)
# ============================================================

from __future__ import annotations

import hashlib
import re
from typing import Tuple

from backend.app.services.code_parser.tokenizer import KEYWORDS

NORMALIZATION_VERSION = "v1.0.0"

# Common built-in types and identifiers that should not be renamed
STANDARD_TYPES = {
    "int", "float", "double", "char", "bool", "boolean", "void", "string", "String",
    "long", "short", "byte", "size_t", "uint32_t", "int32_t", "uint64_t", "int64_t",
    "self", "this", "cls", "true", "false", "null", "nil", "None", "True", "False",
    "console", "print", "println", "printf", "std", "vector", "map", "list", "dict",
    "set", "object", "Object", "Array", "Promise", "Exception", "Error",
}


def remove_comments(code: str, language: str | None = None) -> str:
    """Safely strip single-line and multi-line comments from code without modifying literals."""
    if language == "python":
        # Remove Python comments (#)
        lines = []
        for line in code.splitlines(keepends=True):
            in_quote = False
            quote_char = None
            comment_start = -1
            for i, ch in enumerate(line):
                if ch in ('"', "'"):
                    if not in_quote:
                        in_quote = True
                        quote_char = ch
                    elif quote_char == ch and (i == 0 or line[i - 1] != '\\'):
                        in_quote = False
                elif ch == '#' and not in_quote:
                    comment_start = i
                    break
            if comment_start >= 0:
                lines.append(line[:comment_start].rstrip() + "\n")
            else:
                lines.append(line)
        return "".join(lines)

    # C, C++, Java, JS, TS, Go, Rust, C#, PHP comments (// and /* */)
    pattern = r"""
        (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`)
        | (?P<COMMENT_BLOCK>/\*[\s\S]*?\*/)
        | (?P<COMMENT_LINE>//[^\n]*)
    """
    regex = re.compile(pattern, re.VERBOSE)

    def _repl(match):
        if match.group("COMMENT_BLOCK") or match.group("COMMENT_LINE"):
            return ""
        return match.group(0)

    return regex.sub(_repl, code)


strip_code_comments = remove_comments


def normalize_identifiers(
    code: str, language: str | None = None, strip_comments: bool = False, remove_comments: bool | None = None
) -> Tuple[str, str]:
    """Deterministically map non-keyword identifiers to VAR_1, VAR_2, etc.

    Returns:
        Tuple of (normalized_code, normalized_content_hash)
    """
    if remove_comments is not None:
        strip_comments = remove_comments
    processed_code = strip_code_comments(code, language) if strip_comments else code
    lang_keywords = KEYWORDS.get(language or "", set())

    # Map to track variable renamings deterministically
    identifier_map: dict[str, str] = {}
    counter = 1

    pattern = re.compile(
        r"""
        (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`)
        | (?P<COMMENT_BLOCK>/\*[\s\S]*?\*/)
        | (?P<COMMENT_LINE>(?://|\#)[^\n]*)
        | (?P<IDENTIFIER>[a-zA-Z_$][a-zA-Z0-9_$]*)
        """,
        re.VERBOSE,
    )

    def _replace_identifier(match):
        nonlocal counter
        if match.group("STRING") or match.group("COMMENT_BLOCK") or match.group("COMMENT_LINE"):
            return match.group(0)

        ident = match.group("IDENTIFIER")
        if not ident:
            return match.group(0)

        # Do not rename keywords, standard types, or dunder methods
        if ident in lang_keywords or ident in STANDARD_TYPES or (ident.startswith("__") and ident.endswith("__")):
            return ident

        if ident not in identifier_map:
            identifier_map[ident] = f"VAR_{counter}"
            counter += 1

        return identifier_map[ident]

    normalized_code = pattern.sub(_replace_identifier, processed_code)
    norm_hash = hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()

    return normalized_code, norm_hash
