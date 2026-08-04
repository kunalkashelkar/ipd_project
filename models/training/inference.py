# ============================================================
# Inference Engine
# ============================================================
import torch
import networkx as nx
from models.gnn.architecture import VulnerabilityGAT
from feature_engineering.dataset.builder import GraphDatasetBuilder
from torch_geometric.data import Batch

class ModelInferenceService:
    def __init__(self, checkpoint_path: str, device: str = "cpu"):
        self.device = torch.device(device)
        # Note: In production we'd load hyperparams dynamically from config mapping
        self.model = VulnerabilityGAT(hidden_channels=128, heads=4)
        
        if checkpoint_path and torch.cuda.is_available():
            self.model.load_state_dict(torch.load(checkpoint_path))
        elif checkpoint_path:
            self.model.load_state_dict(torch.load(checkpoint_path, map_location=torch.device('cpu')))
            
        self.model.to(self.device)
        self.model.eval()
        
        # Instantiate dataset builder to convert raw graphs into tensors dynamically
        self.builder = GraphDatasetBuilder(use_mock_codebert=False) # Production = False

    @torch.no_grad()
    def predict(self, cpg: nx.DiGraph) -> dict:
        """Predicts vulnerability from an SA-CPG NetworkX graph."""
        data_obj = self.builder.build_from_networkx(cpg)
        
        # PyG expects a batch, we wrap a single graph into a Batch of size 1
        batch = Batch.from_data_list([data_obj]).to(self.device)
        
        logits = self.model(
            batch.x, 
            batch.edge_index, 
            batch.edge_attr, 
            batch.batch,
            x_struct=getattr(batch, 'x_struct', None),
            x_sec=getattr(batch, 'x_sec', None),
            x_sem=getattr(batch, 'x_sem', None)
        )
        
        # Binary prediction probability
        prob = torch.sigmoid(logits).item()
        
        return {
            "prediction": "Vulnerable" if prob > 0.5 else "Safe",
            "confidence": prob if prob > 0.5 else 1 - prob,
            "probability": prob
        }
