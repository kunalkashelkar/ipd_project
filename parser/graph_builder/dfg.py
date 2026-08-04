# ============================================================
# Graph Builder — DFG Subgraph
# ============================================================
# Joern uses "REACHING_DEF" edges for data-flow (reaching definitions).
# We treat these as the DFG layer: an edge (u → v) means a definition
# at u may reach the use at v.
# ============================================================

from __future__ import annotations

from typing import Any

import networkx as nx
from loguru import logger

from parser.joern.importer import RawGraph

# Joern data-flow edge labels
_DFG_EDGE_LABELS = frozenset({"REACHING_DEF", "CDG", "DOMINATE", "POST_DOMINATE"})

# Primary DFG label exposed in the merged CPG
_PRIMARY_DFG_LABEL = "DFG"


class DFGBuilder:
    """Extracts the Data Flow Graph layer from a :class:`RawGraph`.

    Uses ``REACHING_DEF`` as the primary data-flow edge label from Joern,
    which tracks variable definitions and their reaching uses — the correct
    representation for taint analysis in Phase 3.
    """

    def build(self, raw: RawGraph) -> nx.DiGraph:
        """Build a directed DFG from *raw*.

        Returns:
            A NetworkX DiGraph where an edge (def → use) carries the
            ``variable`` attribute identifying the flowing data.
        """
        g = nx.DiGraph()

        dfg_node_ids: set[str] = set()
        dfg_edges: list[dict[str, Any]] = []

        for edge in raw.edges:
            if edge["label"] in _DFG_EDGE_LABELS:
                dfg_edges.append(edge)
                dfg_node_ids.add(edge["out_v"])
                dfg_node_ids.add(edge["in_v"])

        for node_id in dfg_node_ids:
            props = raw.vertices.get(node_id, {"label": "UNKNOWN"})
            g.add_node(node_id, **props, _layer="DFG")

        for edge in dfg_edges:
            variable = edge.get("properties", {}).get("variable", "")
            g.add_edge(
                edge["out_v"],
                edge["in_v"],
                label=_PRIMARY_DFG_LABEL,
                original_label=edge["label"],
                variable=variable,
                edge_id=edge["id"],
            )

        logger.debug("DFG built — nodes={n} edges={e}", n=g.number_of_nodes(), e=g.number_of_edges())
        return g

    def get_definitions(self, dfg: nx.DiGraph) -> list[dict]:
        """Return nodes that are definition points (have out-edges in DFG)."""
        return [
            {"id": n, **data}
            for n, data in dfg.nodes(data=True)
            if dfg.out_degree(n) > 0
        ]

    def get_uses(self, dfg: nx.DiGraph) -> list[dict]:
        """Return nodes that are use points (have in-edges in DFG)."""
        return [
            {"id": n, **data}
            for n, data in dfg.nodes(data=True)
            if dfg.in_degree(n) > 0
        ]
