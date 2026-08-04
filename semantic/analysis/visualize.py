# ============================================================
# Embedding Analysis & Visualization
# ============================================================
import torch
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from pathlib import Path
from loguru import logger
from torch_geometric.data import Batch

def visualize_embeddings(
    model, 
    dataloader, 
    device, 
    out_path: str = "./results/visualizations/tsne.png",
    method: str = "tsne"
):
    """
    Extracts the graph-level pooled embeddings from the GAT layer and 
    plots them using t-SNE or PCA to verify class separation.
    """
    model.eval()
    
    all_embeddings = []
    all_labels = []
    
    logger.info(f"Extracting pooled graph embeddings for {method.upper()} visualization...")
    
    with torch.no_grad():
        for batch in dataloader:
            batch = batch.to(device)
            
            # Extract inputs
            x_struct = getattr(batch, 'x_struct', None)
            x_sec = getattr(batch, 'x_sec', None)
            x_sem = getattr(batch, 'x_sem', None)
            
            if hasattr(model, 'fusion') and x_struct is not None:
                h = model.fusion(x_struct, x_sec, x_sem)
            else:
                h = batch.x
                
            # Run through GAT encoder
            h = model.encoder(h, batch.edge_index, batch.edge_attr)
            
            # Pool to Graph level
            h_graph = model.pool(h, batch.batch)
            
            all_embeddings.append(h_graph.cpu().numpy())
            all_labels.extend(batch.y.cpu().numpy())
            
    if not all_embeddings:
        logger.warning("No embeddings extracted. DataLoader may be empty.")
        return
        
    X = np.concatenate(all_embeddings, axis=0)
    y = np.array(all_labels)
    
    # 2. Dimensionality Reduction
    if method == "tsne":
        reducer = TSNE(n_components=2, perplexity=30, n_iter=1000, random_state=42)
    else:
        reducer = PCA(n_components=2)
        
    logger.info(f"Running {method.upper()} on {X.shape[0]} samples of dimension {X.shape[1]}...")
    X_reduced = reducer.fit_transform(X)
    
    # 3. Plotting
    plt.figure(figsize=(10, 8))
    
    scatter = plt.scatter(
        X_reduced[:, 0], 
        X_reduced[:, 1], 
        c=y, 
        cmap=plt.cm.coolwarm, 
        alpha=0.6, 
        edgecolors='w', 
        linewidth=0.5
    )
    
    plt.colorbar(scatter, ticks=[0, 1], label='Class (0=Safe, 1=Vulnerable)')
    plt.title(f'GAT Graph Embeddings ({method.upper()})')
    plt.xlabel('Component 1')
    plt.ylabel('Component 2')
    
    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    plt.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved {method.upper()} visualization to {out_path}")
