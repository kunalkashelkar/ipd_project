# ============================================================
# Validation Engine
# ============================================================
import torch
from .metrics import calculate_metrics
import numpy as np


@torch.no_grad()
def valid_epoch(model, dataloader, criterion, device):
    """Executes validation without tracking gradients."""
    model.eval()
    
    total_loss = 0.0
    all_preds = []
    all_targets = []
    all_probs = []
    
    for batch in dataloader:
        batch = batch.to(device)
        
        logits = model(
            batch.x, 
            batch.edge_index, 
            batch.edge_attr, 
            batch.batch,
            x_struct=getattr(batch, 'x_struct', None),
            x_sec=getattr(batch, 'x_sec', None),
            x_sem=getattr(batch, 'x_sem', None)
        )
        loss = criterion(logits, batch.y.float())
        
        total_loss += loss.item() * batch.num_graphs
        
        probs = torch.sigmoid(logits)
        preds = (probs > 0.5).long()
        
        all_probs.extend(probs.cpu().numpy())
        all_preds.extend(preds.cpu().numpy())
        all_targets.extend(batch.y.cpu().numpy())
        
    metrics = calculate_metrics(np.array(all_targets), np.array(all_preds), np.array(all_probs))
    avg_loss = total_loss / len(dataloader.dataset)
    metrics["loss"] = avg_loss
    
    return metrics
