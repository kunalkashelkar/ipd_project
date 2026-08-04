# ============================================================
# Taint Engine — Source Detector
# ============================================================
# Scans a CPG for nodes that represent user-controlled inputs.
# Marks matching nodes with is_source=True and source_category.
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from taint_analysis.engine.rule_loader import RuleLoader

# Joern node labels that can be sources
_SOURCE_ELIGIBLE_LABELS = frozenset({
    "CALL",         # scanf(), recv(), etc.
    "IDENTIFIER",   # argv[i], environ
    "PARAM",        # function parameters named "input", "argv"
    "FIELD_IDENTIFIER",
})

# Common source parameter/variable names
_SOURCE_VARIABLE_NAMES = frozenset({
    "argv", "argc", "environ", "stdin", "input",
    "user_input", "data", "cmd", "command",
})


class SourceDetector:
    """Identifies taint source nodes in a CPG."""

    def detect(self, cpg: nx.DiGraph, rules: RuleLoader) -> list[str]:
        """Find all source nodes in *cpg*, annotate them, and return their IDs.

        Mutates the CPG in-place by setting:
        - ``is_source = True``
        - ``source_category = <category string>``

        Args:
            cpg:   The merged Code Property Graph.
            rules: Pre-loaded rule definitions.

        Returns:
            List of node IDs that were identified as sources.
        """
        source_ids: list[str] = []

        for node_id, attrs in cpg.nodes(data=True):
            node_label = attrs.get("label", "")

            if node_label not in _SOURCE_ELIGIBLE_LABELS:
                continue

            # ── CALL nodes: check function name ───────────
            if node_label == "CALL":
                name = self._extract_call_name(attrs)
                matched, category = rules.is_source(name)
                if matched:
                    self._mark_source(cpg, node_id, category)
                    source_ids.append(node_id)
                    continue

            # ── IDENTIFIER / PARAM: check variable name ───
            if node_label in ("IDENTIFIER", "PARAM", "FIELD_IDENTIFIER"):
                name = self._extract_identifier_name(attrs)
                if name.lower() in _SOURCE_VARIABLE_NAMES:
                    self._mark_source(cpg, node_id, "argv")
                    source_ids.append(node_id)
                    continue
                # Also check if the name itself is a source function
                matched, category = rules.is_source(name)
                if matched:
                    self._mark_source(cpg, node_id, category)
                    source_ids.append(node_id)

        logger.info("Source detection — found {n} source(s)", n=len(source_ids))
        return source_ids

    # ── Private ────────────────────────────────────────────

    def _mark_source(self, cpg: nx.DiGraph, node_id: str, category: str | None) -> None:
        cpg.nodes[node_id]["is_source"] = True
        cpg.nodes[node_id]["source_category"] = category or "unknown"

    def _extract_call_name(self, attrs: dict) -> str:
        """Extract the function name from a CALL node."""
        return str(
            attrs.get("NAME") or
            attrs.get("name") or
            attrs.get("CODE") or
            attrs.get("code") or ""
        ).split("(")[0].strip()

    def _extract_identifier_name(self, attrs: dict) -> str:
        """Extract the identifier/variable name from a node."""
        return str(
            attrs.get("NAME") or
            attrs.get("name") or
            attrs.get("CODE") or
            attrs.get("code") or ""
        ).strip()
