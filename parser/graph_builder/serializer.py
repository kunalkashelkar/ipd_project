# ============================================================
# Graph Builder — Serializer
# ============================================================
# Converts NetworkX graphs to JSON-serialisable dicts and
# computes summary statistics for API responses.
# ============================================================

from __future__ import annotations

from collections import Counter
from typing import Any

import networkx as nx


class GraphSerializer:
    """Converts NetworkX graphs to API-friendly dicts."""

    def to_dict(self, g: nx.DiGraph) -> dict[str, Any]:
        """Produce a flat node+edge JSON dict.

        Schema:
        {
          "nodes": [ { "id": str, "label": str, ...props } ],
          "edges": [ { "source": str, "target": str, "label": str, ...props } ]
        }
        """
        nodes = []
        for node_id, attrs in g.nodes(data=True):
            node: dict[str, Any] = {"id": str(node_id)}
            node.update(self._clean_attrs(attrs))
            nodes.append(node)

        edges = []
        for src, tgt, attrs in g.edges(data=True):
            edge: dict[str, Any] = {"source": str(src), "target": str(tgt)}
            edge.update(self._clean_attrs(attrs))
            edges.append(edge)

        return {"nodes": nodes, "edges": edges}

    def statistics(self, cpg: nx.DiGraph, ast: nx.DiGraph, cfg: nx.DiGraph, dfg: nx.DiGraph) -> dict[str, Any]:
        """Compute summary statistics over all graph layers.

        Returns:
            Dict suitable for inclusion in an API response and metadata.json.
        """
        node_label_counts = Counter(
            data.get("label", "UNKNOWN") for _, data in cpg.nodes(data=True)
        )
        edge_label_counts = Counter(
            data.get("label", "UNKNOWN") for _, _, data in cpg.edges(data=True)
        )

        return {
            "total_nodes": cpg.number_of_nodes(),
            "total_edges": cpg.number_of_edges(),
            "ast_nodes": ast.number_of_nodes(),
            "ast_edges": ast.number_of_edges(),
            "cfg_nodes": cfg.number_of_nodes(),
            "cfg_edges": cfg.number_of_edges(),
            "dfg_nodes": dfg.number_of_nodes(),
            "dfg_edges": dfg.number_of_edges(),
            "function_count": node_label_counts.get("METHOD", 0),
            "call_count": node_label_counts.get("CALL", 0),
            "node_label_distribution": dict(node_label_counts.most_common(20)),
            "edge_label_distribution": dict(edge_label_counts.most_common(10)),
        }

    # ── Private ────────────────────────────────────────────

    def _clean_attrs(self, attrs: dict) -> dict:
        """Make every attribute JSON-serialisable."""
        clean: dict[str, Any] = {}
        for k, v in attrs.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean[k] = v
            elif isinstance(v, (list, tuple)):
                clean[k] = list(v)
            elif isinstance(v, set):
                clean[k] = sorted(v)
            else:
                clean[k] = str(v)
        return clean
