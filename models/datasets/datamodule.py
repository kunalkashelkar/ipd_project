# ============================================================
# DataLoader definitions
# ============================================================
from torch_geometric.loader import DataLoader
from .loader import VulnerabilityDataset
import torch

def create_dataloaders(
    dataset_path: str,
    batch_size: int = 32,
    train_split: float = 0.8,
    val_split: float = 0.1,
    test_split: float = 0.1,
    num_workers: int = 4
):
    """Convenience factory to split a dataset path into DataLoaders."""
    dataset = VulnerabilityDataset(root=dataset_path)
    total_len = len(dataset)
    
    train_len = int(total_len * train_split)
    val_len = int(total_len * val_split)
    test_len = total_len - train_len - val_len
    
    generator = torch.Generator().manual_seed(42)
    train_ds, val_ds, test_ds = torch.utils.data.random_split(
        dataset, [train_len, val_len, test_len], generator=generator
    )
    
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=False, num_workers=num_workers)
    val_loader   = DataLoader(val_ds, batch_size=batch_size, shuffle=False, drop_last=False, num_workers=num_workers)
    test_loader  = DataLoader(test_ds, batch_size=batch_size, shuffle=False, drop_last=False, num_workers=num_workers)
    
    return train_loader, val_loader, test_loader
