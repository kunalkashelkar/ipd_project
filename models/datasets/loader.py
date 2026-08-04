# ============================================================
# PyTorch Geometric Dataset Loader
# ============================================================
import os
from pathlib import Path
from typing import Callable, List, Optional
import torch
from torch_geometric.data import Dataset, Data
from loguru import logger

class VulnerabilityDataset(Dataset):
    """Dynamically loads PyG .pt graph tensors from disk."""
    
    def __init__(
        self, 
        root: str, 
        transform: Optional[Callable] = None, 
        pre_transform: Optional[Callable] = None
    ):
        super().__init__(root, transform, pre_transform)
        
        # In PyG context, `root` is a directory containing `processed/` 
        # But we dumped .pt directly to a path in Phase 4. We'll support direct globbing.
        self.pt_files = []
        if os.path.isdir(root):
            for p in Path(root).rglob("*.pt"):
                self.pt_files.append(str(p))
                
        logger.info(f"Initialized VulnerabilityDataset with {len(self.pt_files)} graphs from {root}")
        
    @property
    def raw_file_names(self) -> List[str]:
        return []

    @property
    def processed_file_names(self) -> List[str]:
        return [Path(p).name for p in self.pt_files]

    def len(self) -> int:
        return len(self.pt_files)

    def get(self, idx: int) -> Data:
        """Load single graph from disk efficiently."""
        file_path = self.pt_files[idx]
        data = torch.load(file_path, weights_only=False)
        return data

