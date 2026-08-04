# ============================================================
# Dataset Serializer & Splitter & Validator
# ============================================================

import os
from pathlib import Path
import torch
from loguru import logger
from torch_geometric.data import Data
from sklearn.model_selection import train_test_split


def save_graph(data: Data, out_path: str):
    """Serialize PyG Data object to .pt format."""
    torch.save(data, out_path)


def load_graph(in_path: str) -> Data:
    """Deserialize PyG Data object from .pt format."""
    return torch.load(in_path)


def validate_graph(data: Data) -> bool:
    """Validate dimensionality and NaN values."""
    if data.x is None or data.edge_index is None:
        return False
    if torch.isnan(data.x).any():
        return False
    if data.x.size(1) != 784:
        logger.warning(f"Feature dimension mismatch. Got {data.x.size(1)}, expected 784")
        return False
    return True


def create_dataset_splits(dataset_indices: list[int], labels: list[int], train_ratio=0.7, val_ratio=0.15):
    """Generate indices for Train/Val/Test stratification."""
    if len(dataset_indices) == 0:
        return [], [], []

    # first split into Train and Temp
    temp_ratio = 1.0 - train_ratio
    train_idx, temp_idx, _, temp_labels = train_test_split(
        dataset_indices, labels, test_size=temp_ratio, stratify=labels, random_state=42
    )

    # second split Temp into Val and Test
    test_ratio_relative = (1.0 - train_ratio - val_ratio) / temp_ratio
    val_idx, test_idx = train_test_split(
        temp_idx, test_size=test_ratio_relative, stratify=temp_labels, random_state=42
    )

    return train_idx, val_idx, test_idx
