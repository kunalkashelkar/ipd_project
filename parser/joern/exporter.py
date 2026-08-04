# ============================================================
# Joern Integration — Graph Exporter
# ============================================================
# Writes the processed CPG (NetworkX DiGraph) to disk as
# graph.json and metadata.json inside the project graph dir.
# ============================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

if TYPE_CHECKING:
    import networkx as nx


class GraphExporter:
    """Serialises a processed CPG to disk in a project-specific directory."""

    def export(
        self,
        cpg: "nx.DiGraph",
        output_dir: Path,
        metadata: dict[str, Any],
    ) -> tuple[Path, Path]:
        """Write the CPG graph and metadata to *output_dir*.

        Args:
            cpg:        The merged CPG NetworkX DiGraph.
            output_dir: Target directory (created if it doesn't exist).
            metadata:   Arbitrary metadata dict (node counts, file list, etc.).

        Returns:
            Tuple of (graph_json_path, metadata_json_path).
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        graph_path = output_dir / "graph.json"
        meta_path = output_dir / "metadata.json"

        # ── Write graph ────────────────────────────────────
        graph_data = self._graph_to_dict(cpg)
        graph_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")

        # ── Write metadata ─────────────────────────────────
        meta_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")

        logger.info(
            "Graph exported — dir={dir} nodes={n} edges={e}",
            dir=output_dir,
            n=cpg.number_of_nodes(),
            e=cpg.number_of_edges(),
        )
        return graph_path, meta_path

    # ── Private helpers ────────────────────────────────────

    def _graph_to_dict(self, g: "nx.DiGraph") -> dict:
        """Convert NetworkX DiGraph to a serialisable dict.

        Format:
        {
          "nodes": [ { "id": str, "label": str, ...properties } ],
          "edges": [ { "source": str, "target": str, "label": str, ...properties } ]
        }
        """
        nodes = []
        for node_id, attrs in g.nodes(data=True):
            node = {"id": str(node_id)}
            node.update({k: _safe_value(v) for k, v in attrs.items()})
            nodes.append(node)

        edges = []
        for src, tgt, attrs in g.edges(data=True):
            edge = {"source": str(src), "target": str(tgt)}
            edge.update({k: _safe_value(v) for k, v in attrs.items()})
            edges.append(edge)

        return {"nodes": nodes, "edges": edges}


def _safe_value(v: Any) -> Any:
    """Convert non-JSON-serialisable values to strings."""
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)
