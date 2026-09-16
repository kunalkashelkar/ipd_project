# ============================================================
# Duplicate Function Detector — Normalized Hash Grouping
# ============================================================

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from backend.app.services.code_parser.extractor import ExtractedFunction


def detect_duplicate_functions(
    functions: Sequence[ExtractedFunction],
) -> dict[str, str]:
    """Group functions by normalized content hash.

    Returns:
        Mapping of function_id -> duplicate_group_id (for functions that have at least 1 duplicate)
    """
    hash_groups: dict[str, list[str]] = defaultdict(list)

    for func in functions:
        norm_hash = func["normalized_content_hash"]
        hash_groups[norm_hash].append(func["function_id"])

    duplicate_map: dict[str, str] = {}
    for norm_hash, func_ids in hash_groups.items():
        if len(func_ids) > 1:
            group_id = f"dup_{norm_hash[:16]}"
            for fid in func_ids:
                duplicate_map[fid] = group_id

    return duplicate_map
