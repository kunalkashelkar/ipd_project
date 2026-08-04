# ============================================================
# Taint Engine — Attack Path Extractor
# ============================================================
# DFS over the tainted DFG subgraph to find all simple paths
# from each (source, sink) pair.
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from taint_analysis.engine.propagation import TaintInfo
from taint_analysis.models.path import AttackPath

# Max path length to guard against exponential blowup
_MAX_PATH_LENGTH = 20
# Max paths per (source, sink) pair to bound runtime
_MAX_PATHS_PER_PAIR = 5


class AttackPathExtractor:
    """Extracts concrete attack paths from a tainted CPG subgraph."""

    def extract(
        self,
        cpg: nx.DiGraph,
        source_ids: list[str],
        sink_ids: list[str],
        sanitizer_ids: set[str],
        taint: dict[str, TaintInfo],
    ) -> list[AttackPath]:
        """Find all attack paths from sources to reachable sinks.

        Algorithm:
        1. Build a tainted DFG subgraph (only tainted nodes + DFG edges).
        2. For each (source, sink) pair where the sink is tainted:
           - Run ``nx.all_simple_paths`` up to depth ``_MAX_PATH_LENGTH``.
           - For each path: check for sanitizers, build AttackPath object.
        3. Return all paths sorted by risk (critical first).

        Args:
            cpg:           Full CPG DiGraph.
            source_ids:    Source node IDs.
            sink_ids:      Sink node IDs.
            sanitizer_ids: Sanitizer node IDs.
            taint:         TaintInfo mapping from propagation step.

        Returns:
            List of :class:`AttackPath` objects, sorted by path length.
        """
        from taint_analysis.engine.propagation import TaintPropagator

        tainted_subgraph = TaintPropagator().get_tainted_subgraph(cpg, taint)

        # Only sinks that were reached by taint
        reachable_sinks = [
            sid for sid in sink_ids
            if taint.get(sid, TaintInfo(sid)).is_tainted
        ]

        paths: list[AttackPath] = []

        for source_id in source_ids:
            if not tainted_subgraph.has_node(source_id):
                continue
            for sink_id in reachable_sinks:
                if not tainted_subgraph.has_node(sink_id):
                    continue
                if source_id == sink_id:
                    continue

                try:
                    raw_paths = list(nx.all_simple_paths(
                        tainted_subgraph,
                        source=source_id,
                        target=sink_id,
                        cutoff=_MAX_PATH_LENGTH,
                    ))
                except nx.NetworkXNoPath:
                    continue
                except nx.NodeNotFound:
                    continue

                for raw_path in raw_paths[:_MAX_PATHS_PER_PAIR]:
                    path = self._build_path(
                        raw_path, source_id, sink_id,
                        cpg, sanitizer_ids,
                    )
                    paths.append(path)

        # Deduplicate by node sequence
        seen: set[tuple] = set()
        unique: list[AttackPath] = []
        for p in paths:
            key = tuple(p.nodes)
            if key not in seen:
                seen.add(key)
                unique.append(p)

        logger.info(
            "Attack path extraction — paths={n} (from {s} sources, {sk} sinks)",
            n=len(unique),
            s=len(source_ids),
            sk=len(reachable_sinks),
        )
        return sorted(unique, key=lambda p: p.length)

    # ── Private helpers ────────────────────────────────────

    def _build_path(
        self,
        node_sequence: list[str],
        source_id: str,
        sink_id: str,
        cpg: nx.DiGraph,
        sanitizer_ids: set[str],
    ) -> AttackPath:
        """Construct an AttackPath from a raw sequence of node IDs."""
        # Collect sanitizer nodes on this path (excluding source/sink)
        sanitizers_on_path = [
            nid for nid in node_sequence[1:-1]
            if nid in sanitizer_ids or cpg.nodes[nid].get("is_sanitized")
        ]

        edges = list(zip(node_sequence, node_sequence[1:]))

        source_attrs = cpg.nodes.get(source_id, {})
        sink_attrs   = cpg.nodes.get(sink_id, {})

        return AttackPath(
            source_node_id=source_id,
            sink_node_id=sink_id,
            nodes=node_sequence,
            edges=edges,
            length=len(node_sequence) - 1,
            sanitized=len(sanitizers_on_path) > 0,
            sanitizer_node_ids=sanitizers_on_path,
            sink_category=str(sink_attrs.get("sink_category", "")),
            source_category=str(source_attrs.get("source_category", "")),
            source_code=str(source_attrs.get("CODE") or source_attrs.get("code", "")),
            sink_code=str(sink_attrs.get("CODE") or sink_attrs.get("code", "")),
            source_line=source_attrs.get("lineNumber") or source_attrs.get("line_number"),
            sink_line=sink_attrs.get("lineNumber") or sink_attrs.get("line_number"),
            filename=sink_attrs.get("filename") or source_attrs.get("filename"),
        )
