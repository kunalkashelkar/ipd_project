# ============================================================
# Taint Engine — Rule Loader
# ============================================================
# Loads sources/sinks/sanitizers JSON rule files and provides
# fast O(1) lookup via pre-computed sets.
# ============================================================

from __future__ import annotations

import json
import re
from pathlib import Path
from functools import lru_cache
from typing import Any

from loguru import logger

_RULES_DIR = Path(__file__).resolve().parents[1] / "rules"


class RuleLoader:
    """Loads and indexes taint analysis rules from JSON files.

    Provides:
    - ``is_source(name)``     → (bool, category | None)
    - ``is_sink(name)``       → (bool, category | None)
    - ``is_sanitizer(name)``  → bool
    - ``matches_bound_check(code)`` → bool (regex patterns)
    """

    def __init__(self, rules_dir: Path | None = None) -> None:
        self._rules_dir = rules_dir or _RULES_DIR
        self._source_map: dict[str, str] = {}      # function_name → category
        self._sink_map: dict[str, str] = {}         # function_name → category
        self._sanitizer_set: set[str] = set()
        self._bound_patterns: list[re.Pattern] = []
        self._validation_keywords: set[str] = set()
        self._load_all()

    # ── Public API ─────────────────────────────────────────

    def is_source(self, name: str) -> tuple[bool, str | None]:
        """Return (True, category) if *name* is a taint source, else (False, None)."""
        name = name.strip()
        cat = self._source_map.get(name) or self._source_map.get(name.lower())
        return (cat is not None, cat)

    def is_sink(self, name: str) -> tuple[bool, str | None]:
        """Return (True, category) if *name* is a taint sink, else (False, None)."""
        name = name.strip()
        cat = self._sink_map.get(name) or self._sink_map.get(name.lower())
        return (cat is not None, cat)

    def is_sanitizer_function(self, name: str) -> bool:
        """Return True if *name* is a known safe/sanitizing function."""
        name = name.strip().lower()
        return name in self._sanitizer_set

    def matches_bound_check(self, code: str) -> bool:
        """Return True if *code* matches a bounds-check / validation pattern."""
        if not code:
            return False
        code_lower = code.lower()
        # Check named validation keywords first (fast)
        for kw in self._validation_keywords:
            if kw in code_lower:
                return True
        # Check regex patterns
        for pattern in self._bound_patterns:
            if pattern.search(code):
                return True
        return False

    @property
    def all_sources(self) -> set[str]:
        return set(self._source_map.keys())

    @property
    def all_sinks(self) -> set[str]:
        return set(self._sink_map.keys())

    @property
    def all_sanitizers(self) -> set[str]:
        return self._sanitizer_set.copy()

    # ── Private helpers ────────────────────────────────────

    def _load_all(self) -> None:
        self._load_sources()
        self._load_sinks()
        self._load_sanitizers()
        logger.debug(
            "Rules loaded — sources={s} sinks={sk} sanitizers={san}",
            s=len(self._source_map),
            sk=len(self._sink_map),
            san=len(self._sanitizer_set),
        )

    def _load_sources(self) -> None:
        data = self._read_json("sources.json")
        for category, entries in data.items():
            if category.startswith("_"):
                continue
            for fn in entries:
                self._source_map[fn] = category
                self._source_map[fn.lower()] = category

    def _load_sinks(self) -> None:
        data = self._read_json("sinks.json")
        for category, entries in data.items():
            if category.startswith("_"):
                continue
            for fn in entries:
                self._sink_map[fn] = category
                self._sink_map[fn.lower()] = category

    def _load_sanitizers(self) -> None:
        data = self._read_json("sanitizers.json")
        for fn in data.get("functions", []):
            self._sanitizer_set.add(fn.lower())
        for fn in data.get("safe_format_functions", []):
            self._sanitizer_set.add(fn.lower())
        for pattern in data.get("bound_check_patterns", []):
            try:
                self._bound_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid sanitizer regex pattern: {p}", p=pattern)
        for kw in data.get("validation_keywords", []):
            self._validation_keywords.add(kw.lower())

    def _read_json(self, filename: str) -> dict[str, Any]:
        path = self._rules_dir / filename
        if not path.exists():
            logger.warning("Rule file not found: {p}", p=path)
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to parse rule file {p}: {e}", p=path, e=e)
            return {}


@lru_cache(maxsize=1)
def get_default_rules() -> RuleLoader:
    """Return the cached default RuleLoader instance."""
    return RuleLoader()
