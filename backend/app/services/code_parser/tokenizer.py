# ============================================================
# Code Tokenizer — Deterministic Language-Aware Tokenization
# ============================================================

from __future__ import annotations

import re
from typing import TypedDict

TOKENIZER_VERSION = "v1.0.0"

# Common language keywords
KEYWORDS = {
    "python": {
        "and", "as", "assert", "async", "await", "break", "class", "continue",
        "def", "del", "elif", "else", "except", "finally", "for", "from",
        "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
        "or", "pass", "raise", "return", "try", "while", "with", "yield",
        "True", "False", "None",
    },
    "c": {
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "int", "long", "register", "return", "short", "signed", "sizeof", "static",
        "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    },
    "cpp": {
        "asm", "auto", "bool", "break", "case", "catch", "char", "class",
        "const", "constexpr", "continue", "default", "delete", "do", "double",
        "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false",
        "float", "for", "friend", "goto", "if", "inline", "int", "long",
        "mutable", "namespace", "new", "noexcept", "nullptr", "operator", "private",
        "protected", "public", "register", "reinterpret_cast", "return", "short",
        "signed", "sizeof", "static", "static_cast", "struct", "switch", "template",
        "this", "throw", "true", "try", "typedef", "typeid", "typename", "union",
        "unsigned", "using", "virtual", "void", "volatile", "while",
    },
    "java": {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
        "class", "const", "continue", "default", "do", "double", "else", "enum",
        "extends", "final", "finally", "float", "for", "goto", "if", "implements",
        "import", "instanceof", "int", "interface", "long", "native", "new",
        "package", "private", "protected", "public", "return", "short", "static",
        "strictfp", "super", "switch", "synchronized", "this", "throw", "throws",
        "transient", "try", "void", "volatile", "while", "true", "false", "null",
    },
    "javascript": {
        "async", "await", "break", "case", "catch", "class", "const", "continue",
        "debugger", "default", "delete", "do", "else", "export", "extends", "finally",
        "for", "function", "if", "import", "in", "instanceof", "let", "new",
        "return", "super", "switch", "this", "throw", "try", "typeof", "var",
        "void", "while", "with", "yield", "true", "false", "null", "undefined",
    },
    "typescript": {
        "async", "await", "break", "case", "catch", "class", "const", "continue",
        "debugger", "default", "delete", "do", "else", "export", "extends", "finally",
        "for", "function", "if", "import", "in", "instanceof", "let", "new",
        "return", "super", "switch", "this", "throw", "try", "typeof", "var",
        "void", "while", "with", "yield", "true", "false", "null", "undefined",
        "interface", "type", "enum", "implements", "declare", "namespace", "readonly",
    },
    "go": {
        "break", "case", "chan", "const", "continue", "default", "defer", "else",
        "fallthrough", "for", "func", "go", "goto", "if", "import", "interface",
        "map", "package", "range", "return", "select", "struct", "switch", "type", "var",
        "true", "false", "nil", "iota",
    },
    "rust": {
        "as", "break", "const", "continue", "crate", "else", "enum", "extern",
        "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod",
        "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct",
        "super", "trait", "true", "type", "unsafe", "use", "where", "while", "async", "await",
    },
    "csharp": {
        "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char",
        "checked", "class", "const", "continue", "decimal", "default", "delegate",
        "do", "double", "else", "enum", "event", "explicit", "extern", "false",
        "finally", "fixed", "float", "for", "foreach", "goto", "if", "implicit",
        "in", "int", "interface", "internal", "is", "lock", "long", "namespace",
        "new", "null", "object", "operator", "out", "override", "params", "private",
        "protected", "public", "readonly", "ref", "return", "sbyte", "sealed",
        "short", "sizeof", "stackalloc", "static", "string", "struct", "switch",
        "this", "throw", "true", "try", "typeof", "uint", "ulong", "unchecked",
        "unsafe", "ushort", "using", "virtual", "void", "volatile", "while",
    },
    "php": {
        "abstract", "and", "array", "as", "break", "callable", "case", "catch", "class",
        "clone", "const", "continue", "declare", "default", "die", "do", "echo", "else",
        "elseif", "empty", "enddeclare", "endfor", "endforeach", "endif", "endswitch",
        "endwhile", "eval", "exit", "extends", "final", "finally", "fn", "for", "foreach",
        "function", "global", "goto", "if", "implements", "include", "include_once",
        "instanceof", "insteadof", "interface", "isset", "list", "namespace", "new",
        "or", "print", "private", "protected", "public", "require", "require_once",
        "return", "static", "switch", "throw", "trait", "try", "unset", "use", "var",
        "while", "xor", "yield", "true", "false", "null",
    },
}

TOKEN_PATTERN = re.compile(
    r"""
    (?P<STRING>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*`)  # Strings
    | (?P<NUMBER>\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)                       # Numbers
    | (?P<IDENTIFIER>[a-zA-Z_$][a-zA-Z0-9_$]*)                             # Identifiers / Keywords
    | (?P<OPERATOR>[+\-*/%=&|<>!^~?:.]+)                                    # Operators
    | (?P<DELIMITER>[()\[\]{},;])                                          # Delimiters
    """,
    re.VERBOSE,
)


class CodeToken(TypedDict):
    type: str
    value: str
    line: int


class TokenizationResult:
    def __init__(self, tokens: list[CodeToken], token_count: int, tokenizer_version: str = TOKENIZER_VERSION):
        self.tokens = tokens
        self.token_count = token_count
        self.tokenizer_version = tokenizer_version

    def to_dict(self) -> dict:
        return {
            "token_count": self.token_count,
            "tokenizer_version": self.tokenizer_version,
            "tokens": self.tokens,
        }


def tokenize_code(code: str, language: str | None = None) -> TokenizationResult:
    """Deterministically tokenize code into typed tokens."""
    tokens: list[CodeToken] = []
    lang_keywords = KEYWORDS.get(language or "", set())

    current_line = 1
    for match in TOKEN_PATTERN.finditer(code):
        # Update line number
        start_idx = match.start()
        # Count newlines prior to token
        # Simple line estimation
        group_name = match.lastgroup or "UNKNOWN"
        val = match.group(group_name)

        if group_name == "IDENTIFIER" and val in lang_keywords:
            token_type = "KEYWORD"
        else:
            token_type = group_name

        tokens.append({
            "type": token_type,
            "value": val,
            "line": current_line,
        })

    return TokenizationResult(tokens=tokens, token_count=len(tokens))


tokenize_source = tokenize_code
