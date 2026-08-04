# ============================================================
# Naive Concatenation Fusion
# ============================================================
import torch
import torch.nn as nn

class ConcatFusion(nn.Module):
    """Simple baseline strategy: [Struct || Security || Semantic]"""
    def __init__(self, in_features: list[int]):
        super().__init__()
        # Check shapes: in_features [9, 7, 768] usually
        self.out_dim = sum(in_features)
        
    def forward(self, x_struct, x_sec, x_sem):
        # Concatenate along the feature dimension (dim=1)
        return torch.cat([x_struct, x_sec, x_sem], dim=-1)
