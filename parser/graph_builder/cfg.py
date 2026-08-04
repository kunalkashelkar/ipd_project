# ============================================================
# Graph Builder — CFG Subgraph
# ============================================================
# Filters the raw CPG to produce a Control Flow Graph where
# edges represent possible execution transitions between statements.
# ============================================================

from __future__ import annotations

from typing import Any

import networkx as nx
from loguru import logger

from parser.joern.importer import RawGraph

# Joern CFG edge label
_CFG_EDGE_LABEL = "CFG"


class CFGBuilder:
    """Extracts the CFG layer from a :class:`RawGraph`."""

    def build(self, raw: RawGraph) -> nx.DiGraph:
        """Build a directed CFG from *raw*.

        Returns:
            A NetworkX DiGraph where an edge (u → v) means control may
            transfer from statement u to statement v.
        """
        g = nx.DiGraph()

        cfg_node_ids: set[str] = set()
        cfg_edges: list[dict[str, Any]] = []

        for edge in raw.edges:
            if edge["label"] == _CFG_EDGE_LABEL:
                cfg_edges.append(edge)
                cfg_node_ids.add(edge["out_v"])
                cfg_node_ids.add(edge["in_v"])

        for node_id in cfg_node_ids:
            props = raw.vertices.get(node_id, {"label": "UNKNOWN"})
            g.add_node(node_id, **props, _layer="CFG")

        for edge in cfg_edges:
            g.add_edge(
                edge["out_v"],
                edge["in_v"],
                label="CFG",
                edge_id=edge["id"],
            )

        logger.debug("CFG built — nodes={n} edges={e}", n=g.number_of_nodes(), e=g.number_of_edges())
        return g

    def get_entry_nodes(self, cfg: nx.DiGraph) -> list[str]:
        """Return nodes with no predecessors (function entry points)."""
        return [n for n in cfg.nodes if cfg.in_degree(n) == 0]

    def get_exit_nodes(self, cfg: nx.DiGraph) -> list[str]:
        """Return nodes with no successors (return / exit points)."""
        return [n for n in cfg.nodes if cfg.out_degree(n) == 0]
