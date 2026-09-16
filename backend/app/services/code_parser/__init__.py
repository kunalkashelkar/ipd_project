# ============================================================
# Code Parser Package (Phase 3)
# ============================================================

from backend.app.services.code_parser.duplicate_detector import detect_duplicate_functions
from backend.app.services.code_parser.extractor import (
    ExtractedFunction,
    extract_functions,
    make_function_id,
)
from backend.app.services.code_parser.language_detector import (
    SUPPORTED_EXTENSIONS,
    detect_file_language,
)
from backend.app.services.code_parser.normalizer import (
    NORMALIZATION_VERSION,
    normalize_identifiers,
    remove_comments,
)
from backend.app.services.code_parser.source_validator import (
    classify_file,
    is_binary_content,
    sanitize_relative_path,
)
from backend.app.services.code_parser.tokenizer import (
    TOKENIZER_VERSION,
    CodeToken,
    TokenizationResult,
    tokenize_code,
)

__all__ = [
    "detect_file_language",
    "SUPPORTED_EXTENSIONS",
    "tokenize_code",
    "TOKENIZER_VERSION",
    "CodeToken",
    "TokenizationResult",
    "normalize_identifiers",
    "remove_comments",
    "NORMALIZATION_VERSION",
    "extract_functions",
    "make_function_id",
    "ExtractedFunction",
    "detect_duplicate_functions",
    "sanitize_relative_path",
    "is_binary_content",
    "classify_file",
]
