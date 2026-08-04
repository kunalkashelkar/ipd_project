# ============================================================
# Graph Builder — AST Subgraph
# ============================================================
# Filters the raw CPG vertices/edges to produce a DiGraph
# containing only nodes reachable via AST edges.
# ============================================================

from __future__ import annotations

from typing import Any

import networkx as nx

from loguru import logger
from parser.joern.importer import RawGraph


# Joern AST edge label
_AST_EDGE_LABEL = "AST"

# Node labels that are meaningful for vulnerability analysis
_INTERESTING_NODE_LABELS = frozenset(
    {
        "METHOD",
        "METHOD_RETURN",
        "PARAM",
        "LOCAL",
        "CALL",
        "IDENTIFIER",
        "LITERAL",
        "RETURN",
        "BLOCK",
        "CONTROL_STRUCTURE",
        "FIELD_IDENTIFIER",
        "TYPE_DECL",
        "MEMBER",
        "JUMP_TARGET",
        "JUMP_LABEL",
    }
)


class ASTBuilder:
    """Extracts the AST layer from a :class:`RawGraph`."""

    def build(self, raw: RawGraph) -> nx.DiGraph:
        """Build a directed AST graph from *raw*.

        Returns:
            A NetworkX DiGraph where edges are AST parent→child relationships.
            Every node carries its full GraphSON properties as attributes.
        """
        g = nx.DiGraph()

        # Collect all node IDs that appear in AST edges
        ast_node_ids: set[str] = set()
        ast_edges: list[dict[str, Any]] = []

        for edge in raw.edges:
            if edge["label"] == _AST_EDGE_LABEL:
                ast_edges.append(edge)
                ast_node_ids.add(edge["out_v"])
                ast_node_ids.add(edge["in_v"])

        # Add nodes (only those in AST edges)
        for node_id in ast_node_ids:
            props = raw.vertices.get(node_id, {"label": "UNKNOWN"})
            g.add_node(node_id, **props, _layer="AST")

        # Add edges
        for edge in ast_edges:
            g.add_edge(
                edge["out_v"],
                edge["in_v"],
                label="AST",
                edge_id=edge["id"],
            )

        logger.debug("AST built — nodes={n} edges={e}", n=g.number_of_nodes(), e=g.number_of_edges())
        return g

    def get_functions(self, ast: nx.DiGraph) -> list[dict]:
        """Return a list of METHOD nodes from the AST."""
        return [
            {"id": n, **data}
            for n, data in ast.nodes(data=True)
            if data.get("label") == "METHOD"
        ]
