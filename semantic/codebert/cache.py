# ============================================================
# Embedding Cache Manager
# ============================================================
import os
import torch
from pathlib import Path
from loguru import logger
import numpy as np

class EmbeddingCache:
    def __init__(self, cache_dir: str = "./datasets/embeddings"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get(self, function_id: str) -> np.ndarray | None:
        """Fetch embedding if it exists."""
        # Use safe filename replacing weird chars
        safe_id = function_id.replace("/", "_").replace("\\", "_")
        path = self.cache_dir / f"{safe_id}.pt"
        
        if path.exists():
            return torch.load(str(path), weights_only=False).numpy()
        return None
        
    def set(self, function_id: str, embedding: np.ndarray):
        """Save embedding to disk."""
        safe_id = function_id.replace("/", "_").replace("\\", "_")
        path = self.cache_dir / f"{safe_id}.pt"
        torch.save(torch.tensor(embedding), str(path))
