# ============================================================
# Gated Fusion
# ============================================================
import torch
import torch.nn as nn

class GatedFusion(nn.Module):
    """
    Uses a gating mechanism (similar to GRU) to determine how much the semantic
    features should update the structural/security base features.
    """
    def __init__(self, in_features: list[int], hidden_dim: int = 256):
        super().__init__()
        self.out_dim = hidden_dim
        
        base_dim = in_features[0] + in_features[1]
        sem_dim = in_features[2]
        
        self.proj_base = nn.Linear(base_dim, hidden_dim)
        self.proj_sem = nn.Linear(sem_dim, hidden_dim)
        
        # Gate controls flow
        self.gate = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Sigmoid()
        )
        
    def forward(self, x_struct, x_sec, x_sem):
        # 1. Base graph structure (struct + taint)
        base = torch.cat([x_struct, x_sec], dim=-1)
        h_base = torch.relu(self.proj_base(base))
        
        # 2. Semantic embeddings
        h_sem = torch.relu(self.proj_sem(x_sem))
        
        # 3. Calculate Gate Z by concatenating them
        z = self.gate(torch.cat([h_base, h_sem], dim=-1))
        
        # 4. Apply gate to semantic, update base
        fused = z * h_base + (1 - z) * h_sem
        
        return fused
