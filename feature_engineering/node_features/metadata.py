# ============================================================
# Node Features — Metadata
# ============================================================
# Extracts non-tensor metadata for bookkeeping and visualization.
# ============================================================

import networkx as nx


def extract_metadata(cpg: nx.DiGraph, node_id: str) -> dict:
    """Extract human-readable metadata for a node."""
    if not cpg.has_node(node_id):
        return {}

    attrs = cpg.nodes[node_id]
    
    return {
        "node_id": str(node_id),
        "label": attrs.get("label", "UNKNOWN"),
        "code": attrs.get("CODE") or attrs.get("code", ""),
        "filename": attrs.get("filename", ""),
        "line_number": attrs.get("lineNumber") or attrs.get("line_number", -1)
    }
