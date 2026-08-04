# ============================================================
# Training Engine
# ============================================================
import torch
import torch.nn as nn
from tqdm import tqdm
from .metrics import calculate_metrics
import numpy as np


def train_epoch(model, dataloader, optimizer, criterion, device):
    """Executes one pass over the training set."""
    model.train()
    
    total_loss = 0.0
    all_preds = []
    all_targets = []
    all_probs = []
    
    # Progress bar omitted if len(dataloader) runs in background, but keeping for standard loops
    for batch in dataloader:
        batch = batch.to(device)
        
        optimizer.zero_grad()
        
        # model forward
        logits = model(
            batch.x, 
            batch.edge_index, 
            batch.edge_attr, 
            batch.batch,
            x_struct=getattr(batch, 'x_struct', None),
            x_sec=getattr(batch, 'x_sec', None),
            x_sem=getattr(batch, 'x_sem', None)
        )
        
        # Loss calculation (BCEWithLogitsLoss expects raw logits)
        loss = criterion(logits, batch.y.float())
        
        loss.backward()
        optimizer.step()
        
        total_loss += loss.item() * batch.num_graphs
        
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).long()
        
        all_probs.extend(probs.detach().cpu().numpy())
        all_preds.extend(preds.detach().cpu().numpy())
        all_targets.extend(batch.y.detach().cpu().numpy())
        
    metrics = calculate_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
    avg_loss = total_loss / len(dataloader.dataset)
    metrics["loss"] = avg_loss
    
    return metrics
