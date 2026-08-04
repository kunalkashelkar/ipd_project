# ============================================================
# Attention-Based Fusion
# ============================================================
import torch
import torch.nn as nn

class AttentionFusion(nn.Module):
    """
    Learns an attention weight for each feature domain before fusing.
    Transforms each modality into a common hidden size, calculates attention,
    and returns a weighted sum.
    """
    def __init__(self, in_features: list[int], hidden_dim: int = 128):
        super().__init__()
        self.out_dim = hidden_dim
        
        # Project each domain to the same dimension
        self.proj_struct = nn.Linear(in_features[0], hidden_dim)
        self.proj_sec    = nn.Linear(in_features[1], hidden_dim)
        self.proj_sem    = nn.Linear(in_features[2], hidden_dim)
        
        # Cross-domain attention scorer
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim, 1),
            nn.LeakyReLU()
        )
        
    def forward(self, x_struct, x_sec, x_sem):
        # 1. Project to common space
        h_str = torch.relu(self.proj_struct(x_struct)) # (N, H)
        h_sec = torch.relu(self.proj_sec(x_sec))
        h_sem = torch.relu(self.proj_sem(x_sem))
        
        # 2. Stack into (N, 3, H) for attention
        stacked = torch.stack([h_str, h_sec, h_sem], dim=1)
        
        # 3. Calculate attention weights (N, 3, 1)
        scores = self.attention(stacked)
        weights = torch.softmax(scores, dim=1) # softmax over the 3 domains
        
        # 4. Weighted sum -> (N, H)
        fused = torch.sum(weights * stacked, dim=1)
        
        return fused
