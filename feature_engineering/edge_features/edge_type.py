# ============================================================
# Edge Features
# ============================================================
# Extracts categorical representations for edge types.
# ============================================================

import networkx as nx
import numpy as np

# Maps Joern/CPG edge types to a categorical embedding index.
_EDGE_TYPES = [
    "AST",
    "CFG",
    "DFG",
    "REACHING_DEF",
    "CALL",
    "RETURN",
    "UNKNOWN"
]
_EDGE_TYPE_MAP = {t: i for i, t in enumerate(_EDGE_TYPES)}


def extract_edge_type(label: str) -> int:
    """Return the integer index for a given edge label."""
    return _EDGE_TYPE_MAP.get(label, _EDGE_TYPE_MAP["UNKNOWN"])


def extract_edge_features(cpg: nx.DiGraph, u: str, v: str, key: int = 0) -> np.ndarray:
    """Extract edge features for a specified edge (u, v) in the SA-CPG.

    For MultiDiGraph, the `key` would be needed, but since we are working
    with DiGraph (or collapsed edges), we just fetch the data.

    Features:
    [0]: edge_type_index (categorical integer)
    [1]: on_attack_path (binary 0/1)
    """
    if not cpg.has_edge(u, v):
        return np.zeros(2, dtype=np.float32)

    attrs = cpg[u][v]
    
    # Sometimes it's stored in layer or label depending on the graph merge logic
    label = attrs.get("label", attrs.get("layer", "UNKNOWN"))
    edge_idx = extract_edge_type(label)
    
    on_attack = 1.0 if attrs.get("on_attack_path") else 0.0
    
    return np.array([edge_idx, on_attack], dtype=np.float32)
