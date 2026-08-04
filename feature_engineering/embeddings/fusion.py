# ============================================================
# Feature Fusion
# ============================================================
# Concatenates structural, security, and semantic vectors.
# ============================================================

import numpy as np

def fuse_node_features(
    structural_feat: np.ndarray, 
    security_feat: np.ndarray, 
    semantic_feat: np.ndarray
) -> np.ndarray:
    """Fuse all node feature branches into a single tensor.
    
    Dimensions:
        Structural: 9 
        Security: 7
        Semantic: 768
        Total: 784
    """
    return np.concatenate([
        structural_feat,
        security_feat,
        semantic_feat
    ], axis=0).astype(np.float32)

def normalize_features(features: np.ndarray, method: str = "min-max") -> np.ndarray:
    """Normalize a batch of feature vectors (N, D).
    
    Args:
        features: numpy array shape (N, D)
        method: "min-max" or "standard"
    """
    if features.shape[0] == 0:
        return features

    # Standardize over D (column-wise)
    # Be careful not to normalize out binary categorical features or structural one-hots
    # Typically only degree counts & distances should be normalized.
    # We will do a generic pass here on specific cols.
    
    # structural columns: idx [1] to [8]
    # security columns:   idx [14] (taint_distance), [15] (risk_score)
    
    result = np.copy(features)
    
    cols_to_norm = [1, 2, 3, 4, 5, 6, 7, 8, 9+5, 9+6] # degrees + distance + score
    
    if method == "min-max":
        for c in cols_to_norm:
            if c >= result.shape[1]:
                continue
            col_min = np.min(result[:, c])
            col_max = np.max(result[:, c])
            if col_max > col_min:
                result[:, c] = (result[:, c] - col_min) / (col_max - col_min)
                
    elif method == "standard":
        for c in cols_to_norm:
            if c >= result.shape[1]:
                continue
            col_mean = np.mean(result[:, c])
            col_std = np.std(result[:, c])
            if col_std > 0:
                result[:, c] = (result[:, c] - col_mean) / col_std
                
    return result
