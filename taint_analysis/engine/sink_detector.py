# ============================================================
# Taint Engine — Sink Detector
# ============================================================
# Scans a CPG for dangerous operation nodes.
# Marks matching nodes with is_sink=True and sink_category.
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from taint_analysis.engine.rule_loader import RuleLoader

_SINK_ELIGIBLE_LABELS = frozenset({"CALL"})


class SinkDetector:
    """Identifies taint sink nodes in a CPG."""

    def detect(self, cpg: nx.DiGraph, rules: RuleLoader) -> list[str]:
        """Find all sink nodes in *cpg*, annotate them, and return their IDs.

        Mutates the CPG in-place by setting:
        - ``is_sink = True``
        - ``sink_category = <vulnerability category string>``

        Args:
            cpg:   The merged Code Property Graph.
            rules: Pre-loaded rule definitions.

        Returns:
            List of node IDs that were identified as sinks.
        """
        sink_ids: list[str] = []

        for node_id, attrs in cpg.nodes(data=True):
            node_label = attrs.get("label", "")

            if node_label not in _SINK_ELIGIBLE_LABELS:
                continue

            name = self._extract_call_name(attrs)
            matched, category = rules.is_sink(name)

            if matched:
                cpg.nodes[node_id]["is_sink"] = True
                cpg.nodes[node_id]["sink_category"] = category
                sink_ids.append(node_id)

        logger.info("Sink detection — found {n} sink(s)", n=len(sink_ids))
        return sink_ids

    # ── Private ────────────────────────────────────────────

    def _extract_call_name(self, attrs: dict) -> str:
        return str(
            attrs.get("NAME") or
            attrs.get("name") or
            attrs.get("CODE") or
            attrs.get("code") or ""
        ).split("(")[0].strip()
