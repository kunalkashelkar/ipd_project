# ============================================================
# Dataset Builder — PyTorch Geometric
# ============================================================
# Converts SA-CPG and feature modules into torch_geometric.data.Data
# ============================================================

import networkx as nx
import torch
from loguru import logger
from torch_geometric.data import Data

from feature_engineering.node_features.structural import extract_structural_features
from feature_engineering.node_features.security import extract_security_features
from feature_engineering.edge_features.edge_type import extract_edge_features
from feature_engineering.embeddings.codebert import CodeBERTEmbedder
from feature_engineering.embeddings.fusion import fuse_node_features
import numpy as np


class GraphDatasetBuilder:
    def __init__(self, use_mock_codebert: bool = True):
        self.codebert = CodeBERTEmbedder(use_mock=use_mock_codebert)

    def build_from_networkx(self, cpg: nx.DiGraph, label: int = 0) -> Data:
        """Converts a NetworkX SA-CPG to a PyTorch Geometric Data object."""
        
        # 1. Map nodes to 0-indexed integers for edge_index mapping
        node_list = list(cpg.nodes())
        node_to_idx = {n: i for i, n in enumerate(node_list)}
        
        # 2. Extract node features
        n_nodes = len(node_list)
        structural_feats = np.zeros((n_nodes, 9), dtype=np.float32)
        security_feats = np.zeros((n_nodes, 7), dtype=np.float32)
        codes = []
        
        for i, n in enumerate(node_list):
            structural_feats[i] = extract_structural_features(cpg, n)
            security_feats[i] = extract_security_features(cpg, n)
            attrs = cpg.nodes[n]
            # fallback to function name if no code body
            codes.append(attrs.get("CODE") or attrs.get("code") or attrs.get("name") or "")
            
        # CodeBERT Embeddings
        # Extract per node
        semantic_feats = self.codebert.encode_batch(codes)
        
        # Fusion (we fuse them to create [N, 784])
        # x is essentially the concatenated arrays
        x_np = np.concatenate([structural_feats, security_feats, semantic_feats], axis=1)
        x = torch.tensor(x_np, dtype=torch.float32)
        
        # 3. Extract edge features and edge_index
        edges = list(cpg.edges(data=True))
        n_edges = len(edges)
        
        edge_index = torch.zeros((2, n_edges), dtype=torch.long)
        edge_attr = torch.zeros((n_edges, 2), dtype=torch.float32)
        
        for i, (u, v, data) in enumerate(edges):
            edge_index[0, i] = node_to_idx[u]
            edge_index[1, i] = node_to_idx[v]
            
            edge_attr[i] = torch.tensor(extract_edge_features(cpg, u, v), dtype=torch.float32)
            
        # Determine graph-level label (Vulnerable vs Safe)
        # Often provided externally when sweeping datasets (e.g., 1 for vulns, 0 for safe)
        y = torch.tensor([label], dtype=torch.long)
        
        # We can also attach raw node ids for explainability tracing mapping later
        node_ids = [str(n) for n in node_list]
        
        data_obj = Data(
            x=x,
            x_struct=torch.tensor(structural_feats, dtype=torch.float32),
            x_sec=torch.tensor(security_feats, dtype=torch.float32),
            x_sem=torch.tensor(semantic_feats, dtype=torch.float32),
            edge_index=edge_index,
            edge_attr=edge_attr,
            y=y,
            node_ids=node_ids
        )
        
        return data_obj
