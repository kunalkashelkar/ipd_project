# ============================================================
# Joern Integration — GraphSON Importer
# ============================================================
# Reads the JSON files produced by joern-export --format graphson
# and returns a unified raw graph dict with vertices and edges.
# ============================================================

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger


class GraphSONImportError(Exception):
    """Raised when GraphSON files cannot be read or parsed."""


class RawGraph:
    """Container for raw vertices and edges loaded from GraphSON.

    Attributes:
        vertices: Mapping from node ID → vertex property dict.
        edges:    List of raw edge dicts (id, label, outV, inV, properties).
    """

    def __init__(
        self,
        vertices: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        self.vertices = vertices
        self.edges = edges

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def __repr__(self) -> str:
        return f"RawGraph(vertices={self.vertex_count}, edges={self.edge_count})"


class GraphSONImporter:
    """Reads GraphSON JSON files exported by Joern into a :class:`RawGraph`."""

    def load(self, export_dir: Path) -> RawGraph:
        """Load all ``.json`` files in *export_dir* and merge into one RawGraph.

        Args:
            export_dir: Directory written by ``joern-export``.

        Returns:
            A :class:`RawGraph` holding all vertices and edges.

        Raises:
            GraphSONImportError: If no JSON files are found or a file is corrupt.
        """
        json_files = sorted(export_dir.glob("*.json"))
        if not json_files:
            # Also look one level deeper (joern sometimes nests by repr)
            json_files = sorted(export_dir.rglob("*.json"))
        if not json_files:
            raise GraphSONImportError(
                f"No JSON files found in '{export_dir}'. "
                "Ensure joern-export ran successfully."
            )

        all_vertices: dict[str, dict[str, Any]] = {}
        all_edges: list[dict[str, Any]] = []

        for jf in json_files:
            v, e = self._parse_file(jf)
            # Merge — vertices are keyed by their ID so duplicates are naturally deduplicated
            all_vertices.update(v)
            all_edges.extend(e)

        graph = RawGraph(all_vertices, all_edges)
        logger.info(
            "GraphSON loaded — files={n} vertices={v} edges={e}",
            n=len(json_files),
            v=graph.vertex_count,
            e=graph.edge_count,
        )
        return graph

    # ── Private helpers ────────────────────────────────────

    def _parse_file(
        self, path: Path
    ) -> tuple[dict[str, dict], list[dict]]:
        """Parse a single GraphSON file.

        GraphSON v2 / TinkerPop 3 format:
        {
          "vertices": [ { "id": .., "label": .., "properties": { ... } } ],
          "edges":    [ { "id": .., "label": .., "outV": .., "inV": .. } ]
        }
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            raise GraphSONImportError(f"Failed to parse '{path}': {e}") from e

        vertices: dict[str, dict] = {}
        edges: list[dict] = []

        # Handle both top-level list (legacy) and {"vertices": [], "edges": []} object
        if isinstance(data, list):
            # Flat list of elements — discriminate by presence of "outV"
            for item in data:
                if "outV" in item:
                    edges.append(self._normalise_edge(item))
                else:
                    vid, props = self._normalise_vertex(item)
                    vertices[vid] = props
        elif isinstance(data, dict):
            for item in data.get("vertices", []):
                vid, props = self._normalise_vertex(item)
                vertices[vid] = props
            for item in data.get("edges", []):
                edges.append(self._normalise_edge(item))

        return vertices, edges

    def _normalise_vertex(self, raw: dict) -> tuple[str, dict]:
        """Extract id and flatten properties from a GraphSON vertex."""
        vid = str(raw.get("id", raw.get("_id", "")))
        props: dict = {"label": raw.get("label", "UNKNOWN")}

        # GraphSON v2 wraps each property value in {"@type": .., "@value": ..}
        for key, val in raw.get("properties", {}).items():
            if isinstance(val, list) and val:
                inner = val[0]
                if isinstance(inner, dict):
                    props[key] = inner.get("value", inner.get("@value", inner))
                else:
                    props[key] = inner
            elif isinstance(val, dict):
                props[key] = val.get("@value", val)
            else:
                props[key] = val

        return vid, props

    def _normalise_edge(self, raw: dict) -> dict:
        """Normalise an edge dict to a consistent shape."""
        return {
            "id": str(raw.get("id", raw.get("_id", ""))),
            "label": raw.get("label", "UNKNOWN"),
            "out_v": str(raw.get("outV", raw.get("_outV", ""))),
            "in_v": str(raw.get("inV", raw.get("_inV", ""))),
            "properties": raw.get("properties", {}),
        }
