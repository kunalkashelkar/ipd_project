# ============================================================
# Node Features — Security (Taint)
# ============================================================
# Extracts security semantics appended by Phase 3.
# ============================================================

import networkx as nx
import numpy as np


def extract_security_features(cpg: nx.DiGraph, node_id: str) -> np.ndarray:
    """Extract security/taint features for a specific node in the SA-CPG.

    Features: (Binary 0/1 or floats)
    [0]: is_source (bool -> 0/1)
    [1]: is_sink (bool -> 0/1)
    [2]: is_sanitized (bool -> 0/1)
    [3]: is_tainted (bool -> 0/1)
    [4]: on_attack_path (bool -> 0/1)
    [5]: taint_distance (float, -1 if untainted, otherwise normalized later)
    [6]: risk_score (float, 0.0 - 10.0)
    """
    if not cpg.has_node(node_id):
        return np.array([0, 0, 0, 0, 0, -1, 0], dtype=np.float32)

    attrs = cpg.nodes[node_id]
    
    is_source      = 1.0 if attrs.get("is_source") else 0.0
    is_sink        = 1.0 if attrs.get("is_sink") else 0.0
    is_sanitized   = 1.0 if attrs.get("is_sanitized") else 0.0
    is_tainted     = 1.0 if attrs.get("is_tainted") else 0.0
    on_attack_path = 1.0 if attrs.get("on_attack_path") else 0.0
    
    taint_dist = float(attrs.get("taint_distance", -1.0))
    risk_score = float(attrs.get("risk_score", 0.0))
    
    return np.array([
        is_source,
        is_sink,
        is_sanitized,
        is_tainted,
        on_attack_path,
        taint_dist,
        risk_score
    ], dtype=np.float32)
