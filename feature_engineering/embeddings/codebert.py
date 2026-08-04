# ============================================================
# CodeBERT Semantic Embeddings
# ============================================================
# Wraps huggingface transformers to encode code snippets.
# ============================================================

import os
import numpy as np
import torch
from loguru import logger
from transformers import AutoTokenizer, AutoModel

_MOCK_CODEBERT = os.getenv("USE_MOCK_CODEBERT", "true").lower() == "true"
_CODEBERT_MODEL_NAME = "microsoft/codebert-base"

class CodeBERTEmbedder:
    """Generates 768-D semantic embeddings for code snippets using CodeBERT.

    If USE_MOCK_CODEBERT=true is set in the environment, it returns
    deterministic random pseudo-embeddings for fast local testing.
    """
    def __init__(self, use_mock: bool = _MOCK_CODEBERT):
        self.use_mock = use_mock
        self.tokenizer = None
        self.model = None
        
        if self.use_mock:
            logger.info("CodeBERTEmbedder initialized in MOCK mode.")
        else:
            logger.info(f"Loading CodeBERT model: {_CODEBERT_MODEL_NAME}...")
            self.tokenizer = AutoTokenizer.from_pretrained(_CODEBERT_MODEL_NAME)
            self.model = AutoModel.from_pretrained(_CODEBERT_MODEL_NAME)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            logger.info("CodeBERT loaded onto device: {}", self.device)

    def encode(self, code: str) -> np.ndarray:
        """Encode a single code snippet into a 768-D vector."""
        if not code or not code.strip():
            return np.zeros(768, dtype=np.float32)

        if self.use_mock:
            # Deterministic pseudo-random vector based on string hash
            # just so embeddings of similar code are identical
            rng = np.random.RandomState(abs(hash(code)) % (2**32))
            return rng.normal(loc=0.0, scale=0.1, size=768).astype(np.float32)
        
        # Real CodeBERT execution
        inputs = self.tokenizer(
            code,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use [CLS] token embedding as the sequence representation
            cls_embedding = outputs.last_hidden_state[0, 0, :].cpu().numpy()
            
        return cls_embedding.astype(np.float32)

    def encode_batch(self, codes: list[str]) -> np.ndarray:
        """Encode a list of snippets into an (N, 768) matrix."""
        if not codes:
            return np.zeros((0, 768), dtype=np.float32)
        
        if self.use_mock:
            return np.stack([self.encode(c) for c in codes])

        inputs = self.tokenizer(
            codes,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            cls_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            
        return cls_embeddings.astype(np.float32)
