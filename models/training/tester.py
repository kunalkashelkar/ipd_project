# ============================================================
# Test Engine wrapper
# ============================================================
from .validator import valid_epoch

def test_model(model, test_dataloader, criterion, device):
    """Evaluates the model on the unseen test set."""
    # Under the hood it operates exactly like validation
    return valid_epoch(model, test_dataloader, criterion, device)
