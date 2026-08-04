# ============================================================
# Graph Attention Network (GAT) Layers
# ============================================================

import torch
import torch.nn as nn
from torch_geometric.nn import GATConv


class GATEncoder(nn.Module):
    """Multi-layer Graph Attention Network encoder for node embeddings."""
    
    def __init__(
        self,
        in_channels: int,
        hidden_channels: int,
        num_layers: int = 3,
        heads: int = 4,
        dropout: float = 0.2,
        concat: bool = False
    ):
        super().__init__()
        self.num_layers = num_layers
        self.dropout = dropout
        
        self.convs = nn.ModuleList()
        self.norms = nn.ModuleList()
        
        # We handle edge features (dim=2) in our graph
        edge_dim = 2 
        
        for i in range(num_layers):
            in_dim = in_channels if i == 0 else hidden_channels * heads if concat else hidden_channels
            
            self.convs.append(
                GATConv(
                    in_channels=in_dim,
                    out_channels=hidden_channels,
                    heads=heads,
                    concat=concat,
                    dropout=dropout,
                    edge_dim=edge_dim
                )
            )
            # Batch Normalization for stability
            norm_dim = hidden_channels * heads if concat else hidden_channels
            self.norms.append(nn.BatchNorm1d(norm_dim))
            
        self.activation = nn.ELU()
        
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_attr: torch.Tensor, explain_mode: bool = False):
        """Forward pass generating updated node embeddings."""
        attention_weights = []
        
        for i in range(self.num_layers):
            if explain_mode:
                x, attn = self.convs[i](x, edge_index, edge_attr=edge_attr, return_attention_weights=True)
                attention_weights.append(attn)
            else:
                x = self.convs[i](x, edge_index, edge_attr=edge_attr)
                
            x = self.norms[i](x)
            
            # No activation on the final layer for standard GNN encoders
            if i != self.num_layers - 1:
                x = self.activation(x)
                x = nn.functional.dropout(x, p=self.dropout, training=self.training)
                
        if explain_mode:
            return x, attention_weights
        return x
