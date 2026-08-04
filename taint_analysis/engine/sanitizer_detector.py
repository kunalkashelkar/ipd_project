# ============================================================
# Taint Engine — Sanitizer Detector
# ============================================================
# Identifies nodes that neutralise taint — either through safe
# API calls or through bounds-checking control structures.
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from taint_analysis.engine.rule_loader import RuleLoader

_SANITIZER_ELIGIBLE_LABELS = frozenset({
    "CALL",
    "CONTROL_STRUCTURE",  # if-statements that do bounds checks
    "BLOCK",
})


class SanitizerDetector:
    """Identifies nodes that sanitize or validate tainted data."""

    def detect(self, cpg: nx.DiGraph, rules: RuleLoader) -> list[str]:
        """Find all sanitizer nodes in *cpg*, annotate, and return their IDs.

        Mutates the CPG in-place by setting:
        - ``is_sanitized = True``

        Args:
            cpg:   The merged Code Property Graph.
            rules: Pre-loaded rule definitions.

        Returns:
            List of node IDs that were identified as sanitizers.
        """
        sanitizer_ids: list[str] = []

        for node_id, attrs in cpg.nodes(data=True):
            node_label = attrs.get("label", "")

            if node_label not in _SANITIZER_ELIGIBLE_LABELS:
                continue

            is_san = False

            # ── Safe API call ──────────────────────────────
            if node_label == "CALL":
                name = self._extract_call_name(attrs)
                if rules.is_sanitizer_function(name):
                    is_san = True

            # ── Bounds-checking control structure ──────────
            if node_label in ("CONTROL_STRUCTURE", "BLOCK", "CALL"):
                code = str(attrs.get("CODE") or attrs.get("code", ""))
                if rules.matches_bound_check(code):
                    is_san = True

            if is_san:
                cpg.nodes[node_id]["is_sanitized"] = True
                sanitizer_ids.append(node_id)

        logger.info("Sanitizer detection — found {n} sanitizer(s)", n=len(sanitizer_ids))
        return sanitizer_ids

    # ── Private ────────────────────────────────────────────

    def _extract_call_name(self, attrs: dict) -> str:
        return str(
            attrs.get("NAME") or
            attrs.get("name") or
            attrs.get("CODE") or
            attrs.get("code") or ""
        ).split("(")[0].strip()
