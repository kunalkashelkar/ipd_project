# ============================================================
# Advanced CodeBERT Model Wrapper
# ============================================================
import os
import torch
import numpy as np
from loguru import logger
from transformers import AutoTokenizer, AutoModel

_MODEL_NAME = "microsoft/codebert-base"

class AdvancedCodeBERTEmbedder:
    """Provides frozen or fine-tunable CodeBERT extraction."""
    
    def __init__(self, mode: str = "frozen", device: str = None):
        """
        mode: "frozen" (default) or "pooler" (just fine-tune pooler) or "full"
        """
        self.device = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))
        self.mode = mode
        
        logger.info(f"Loading {_MODEL_NAME} in '{mode}' mode onto {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
        self.model = AutoModel.from_pretrained(_MODEL_NAME)
        
        if mode == "frozen":
            self.model.eval()
            for param in self.model.parameters():
                param.requires_grad = False
        elif mode == "pooler":
            # Freeze all but the last few layers and pooler
            for name, param in self.model.named_parameters():
                if "pooler" not in name and "encoder.layer.11" not in name:
                    param.requires_grad = False
                else:
                    param.requires_grad = True
                    
        self.model.to(self.device)

    def encode(self, code: str) -> np.ndarray:
        if not code or not str(code).strip():
            return np.zeros(768, dtype=np.float32)
            
        inputs = self.tokenizer(
            code, return_tensors="pt", truncation=True, max_length=512, padding=True
        ).to(self.device)
        
        if self.mode == "frozen":
            with torch.no_grad():
                outputs = self.model(**inputs)
        else:
            outputs = self.model(**inputs)
            
        # [CLS] token embedding
        cls_embedding = outputs.last_hidden_state[0, 0, :]
        return cls_embedding.detach().cpu().numpy().astype(np.float32)
        
    def encode_batch(self, codes: list[str]) -> np.ndarray:
        if not codes:
            return np.zeros((0, 768), dtype=np.float32)
            
        inputs = self.tokenizer(
            codes, return_tensors="pt", truncation=True, max_length=512, padding=True
        ).to(self.device)
        
        if self.mode == "frozen":
            with torch.no_grad():
                outputs = self.model(**inputs)
        else:
            outputs = self.model(**inputs)
            
        cls_embeddings = outputs.last_hidden_state[:, 0, :]
        return cls_embeddings.detach().cpu().numpy().astype(np.float32)
