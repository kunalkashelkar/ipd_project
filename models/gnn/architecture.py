# ============================================================
# Full Model Architecture — Vulnerability GAT
# ============================================================

import torch
import torch.nn as nn
from loguru import logger

from .gat import GATEncoder
from .pooling import GraphPooler
from semantic.fusion.concat import ConcatFusion
from semantic.fusion.attention import AttentionFusion
from semantic.fusion.gated import GatedFusion


class VulnerabilityGAT(nn.Module):
    """Predicts if a code graph represents a vulnerability."""
    
    def __init__(
        self,
        in_channels: int = 784,   # Default if using monolithic 'x'
        in_features: list[int] = [9, 7, 768], 
        hidden_channels: int = 128,
        num_layers: int = 3,
        heads: int = 3,
        dropout: float = 0.3,
        pooling_type: str = "mean",
        fusion_strategy: str = "concat"
    ):
        super().__init__()
        self.fusion_strategy = fusion_strategy
        
        logger.info(f"Initializing VulnerabilityGAT: hidden={hidden_channels}, fusion={fusion_strategy}")
        
        if fusion_strategy == "attention":
            self.fusion = AttentionFusion(in_features, hidden_dim=hidden_channels)
            gnn_in_channels = self.fusion.out_dim
        elif fusion_strategy == "gated":
            self.fusion = GatedFusion(in_features, hidden_dim=hidden_channels)
            gnn_in_channels = self.fusion.out_dim
        else: # concat or baseline
            self.fusion = ConcatFusion(in_features)
            gnn_in_channels = self.fusion.out_dim
            
        # Node Embedding Encoder
        self.encoder = GATEncoder(
            in_channels=gnn_in_channels,
            hidden_channels=hidden_channels,
            num_layers=num_layers,
            heads=heads,
            dropout=dropout,
            concat=False  # If True, output gets multiplied by heads. Keep false for standard dim
        )
        
        # Graph Pooling
        self.pool = GraphPooler(pooling_type=pooling_type)
        
        # Classification Head (Binary Classification -> 1 output logit)
        self.classifier = nn.Sequential(
            nn.Linear(hidden_channels, hidden_channels // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_channels // 2, 1)
        )
        
    def forward(self, x, edge_index, edge_attr, batch, x_struct=None, x_sec=None, x_sem=None, explain_mode=False):
        """
        Supports monolithic 'x' or decomposed x_struct, x_sec, x_sem arrays.
        If explain_mode is True, returns node-level outputs directly instead of pooling.
        """
        # 1. Advanced Fusion Injection (if explicit tensors are provided)
        if hasattr(self, 'fusion') and x_struct is not None and x_sec is not None and x_sem is not None:
            h = self.fusion(x_struct, x_sec, x_sem)
        else:
            h = x # Fallback to pre-concatenated baseline

        # 2. Update node embeddings via messaging
        if explain_mode:
            h, attentions = self.encoder(h, edge_index, edge_attr, explain_mode=True)
            # When explaining node attribution, we must return the logits directly without global pooling
            # This relies on Explainer targeting specific graph-level logits correctly.
            h_graph = self.pool(h, batch)
            logits = self.classifier(h_graph).squeeze(-1)
            # Normally we might return h as well if node-level reasoning is needed,
            # but PyG Explainer requires the exact output shape to match standard logits.
            return logits
            
        h = self.encoder(h, edge_index, edge_attr)
        
        # 3. Pool nodes into a graph embedding
        h_graph = self.pool(h, batch)
        
        # 4. Classify
        logits = self.classifier(h_graph)
        
        return logits.squeeze(-1)
