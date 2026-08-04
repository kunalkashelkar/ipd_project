# ============================================================
# Graph Features — Statistics
# ============================================================
# Extracts macro-statistics from the full CPG.
# ============================================================

import networkx as nx
import numpy as np


def extract_graph_features(cpg: nx.DiGraph) -> np.ndarray:
    """Extract graph-level aggregate statistics.

    Features:
    [0]: num_nodes
    [1]: num_edges
    [2]: num_functions (METHOD nodes)
    [3]: num_sources
    [4]: num_sinks
    [5]: num_sanitized
    [6]: num_tainted_nodes
    [7]: has_attack_path (binary 0/1)
    [8]: max_risk_score (0.0 to 10.0)
    """
    num_nodes = cpg.number_of_nodes()
    num_edges = cpg.number_of_edges()
    
    num_methods = 0
    num_sources = 0
    num_sinks = 0
    num_sanitizers = 0
    num_tainted = 0
    has_attack_path = 0.0
    max_risk = 0.0
    
    for _, attrs in cpg.nodes(data=True):
        if attrs.get("label") == "METHOD":
            num_methods += 1
        if attrs.get("is_source"):
            num_sources += 1
        if attrs.get("is_sink"):
            num_sinks += 1
        if attrs.get("is_sanitized"):
            num_sanitizers += 1
        if attrs.get("is_tainted"):
            num_tainted += 1
        if attrs.get("on_attack_path"):
            has_attack_path = 1.0
        
        risk = float(attrs.get("risk_score", 0.0))
        if risk > max_risk:
            max_risk = risk

    return np.array([
        float(num_nodes),
        float(num_edges),
        float(num_methods),
        float(num_sources),
        float(num_sinks),
        float(num_sanitizers),
        float(num_tainted),
        has_attack_path,
        max_risk
    ], dtype=np.float32)
