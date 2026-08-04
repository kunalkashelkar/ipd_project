# ============================================================
# Graph Pooling Layers
# ============================================================

import torch
import torch.nn as nn
from torch_geometric.nn import global_mean_pool, global_max_pool, global_add_pool


class GraphPooler(nn.Module):
    """Reduces entire graph node embeddings into a single graph embedding."""
    
    def __init__(self, pooling_type: str = "mean"):
        super().__init__()
        self.pooling_type = pooling_type
        
    def forward(self, x: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Node embeddings (N, D)
            batch: Batch vector assigning each node to a graph (N,)
        Returns:
            Graph embeddings (B, D)
        """
        if self.pooling_type == "mean":
            return global_mean_pool(x, batch)
        elif self.pooling_type == "max":
            return global_max_pool(x, batch)
        elif self.pooling_type == "sum" or self.pooling_type == "add":
            return global_add_pool(x, batch)
        else:
            raise ValueError(f"Unknown pooling type: {self.pooling_type}")
