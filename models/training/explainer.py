# ============================================================
# Explainable AI Wrapper (Captum Integration)
# ============================================================
import torch
import torch.nn as nn
from loguru import logger

try:
    from torch_geometric.explain import Explainer, CaptumExplainer
    from torch_geometric.explain.config import ModelConfig, ExplainerConfig
except ImportError:
    pass

class CaptumExplainerService:
    """
    Wraps the trained VulnerabilityGAT model and uses Captum's 
    IntegratedGradients to assign relevance scores to specific edges (and nodes) 
    that heavily influenced the prediction.
    """
    def __init__(self, model: nn.Module, device: str = "cpu"):
        self.device = torch.device(device)
        self.model = model.to(self.device)
        self.model.eval()
        
        # 1. We must configure the PyG Explainer configs
        # ModelConfig defines how the GNN inputs/outputs behave
        self.model_config = ModelConfig(
            mode='binary_classification', # Big-Vul output
            task_level='graph',         # We are classifying entire CPGs
            return_type='raw',          # We return logits out of `forward`
        )
        
        # ExplainerConfig defines what we are trying to mask/explain
        self.explainer_config = ExplainerConfig(
            explanation_type='model',
            edge_mask_type='object',    # We want to identify critical graph edges
            node_mask_type='object',    # Identify critical nodes (code lines)
        )
        
        # Initialize the actual PyG Explainer wrapping our Captum IntegratedGradients logic
        self.explainer = Explainer(
            model=self.model,
            algorithm=CaptumExplainer('IntegratedGradients'),
            explanation_type='model',
            model_config=self.model_config,
            node_mask_type='object',
            edge_mask_type='object',
        )
        
    def explain_graph(self, data) -> dict:
        """
        Executes the explanation backward pass on a PyG Data object.
        Retrieves node and edge masks.
        """
        data = data.to(self.device)
        
        # Generate the explanation
        # Captum Explainer works by perturbing inputs through the forward pass
        explanation = self.explainer(
            x=data.x, 
            edge_index=data.edge_index, 
            edge_attr=data.edge_attr, 
            batch=data.batch,
            # We must pass the decoupled parameters required by our new forward pass
            x_struct=getattr(data, 'x_struct', None),
            x_sec=getattr(data, 'x_sec', None),
            x_sem=getattr(data, 'x_sem', None),
            explain_mode=False  # Standard graph-level explanation targets the pooled logit
        )
        
        cpg_explanation = {
            "node_importance": explanation.node_mask.detach().cpu().numpy().tolist() if explanation.node_mask is not None else [],
            "edge_importance": explanation.edge_mask.detach().cpu().numpy().tolist() if explanation.edge_mask is not None else [],
        }
        
        return cpg_explanation
