# ============================================================
# Node Features — Structural
# ============================================================
# Extracts topological network features from a node.
# ============================================================

import networkx as nx
import numpy as np

# Maps Joern/CPG node types to a categorical embedding index or one-hot vector.
_NODE_TYPES = [
    "METHOD", "METHOD_PARAMETER_IN", "METHOD_RETURN", "BLOCK", 
    "CALL", "CONTROL_STRUCTURE", "IDENTIFIER", "LITERAL", 
    "LOCAL", "RETURN", "UNKNOWN", "META_DATA", "FILE", "METHOD_PARAMETER_OUT",
    "TYPE_DECL", "TYPE", "TYPE_PARAMETER", "ANNOTATION", "ANNOTATION_PARAMETER_ASSIGN",
    "JUMP_TARGET", "MODIFIER"
]
_NODE_TYPE_MAP = {t: i for i, t in enumerate(_NODE_TYPES)}


def extract_node_type(label: str) -> int:
    """Return the integer index for a given node label.
    UNKNOWN is mapped to a default index if not found.
    """
    return _NODE_TYPE_MAP.get(label, _NODE_TYPE_MAP["UNKNOWN"])


def extract_structural_features(cpg: nx.DiGraph, node_id: str) -> np.ndarray:
    """Extract structural features for a specific node in the CPG.

    Features:
    [0]: node_type_index (integer encoding to be passed to an Embedding layer later, or one-hot)
    [1]: in_degree (total)
    [2]: out_degree (total)
    [3]: ast_in_degree
    [4]: ast_out_degree
    [5]: cfg_in_degree
    [6]: cfg_out_degree
    [7]: dfg_in_degree
    [8]: dfg_out_degree
    """
    if not cpg.has_node(node_id):
        return np.zeros(9, dtype=np.float32)

    attrs = cpg.nodes[node_id]
    label = attrs.get("label", "UNKNOWN")
    type_idx = extract_node_type(label)
    
    in_deg = cpg.in_degree(node_id)
    out_deg = cpg.out_degree(node_id)
    
    ast_in, ast_out = 0, 0
    cfg_in, cfg_out = 0, 0
    dfg_in, dfg_out = 0, 0

    for u, v, data in cpg.in_edges(node_id, data=True):
        edge_label = data.get("label", "")
        if edge_label == "AST": ast_in += 1
        elif edge_label == "CFG": cfg_in += 1
        elif edge_label in ["DFG", "REACHING_DEF"]: dfg_in += 1
        
    for u, v, data in cpg.out_edges(node_id, data=True):
        edge_label = data.get("label", "")
        if edge_label == "AST": ast_out += 1
        elif edge_label == "CFG": cfg_out += 1
        elif edge_label in ["DFG", "REACHING_DEF"]: dfg_out += 1
        
    # Later normalization will scale these degrees
    return np.array([
        type_idx,
        in_deg, out_deg,
        ast_in, ast_out,
        cfg_in, cfg_out,
        dfg_in, dfg_out
    ], dtype=np.float32)

