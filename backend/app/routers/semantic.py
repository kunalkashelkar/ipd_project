# ============================================================
# Semantic CodeBERT Router
# ============================================================
# Exposes direct embedding endpoints for LLM interaction debugging
# ============================================================
import numpy as np
from fastapi import APIRouter, HTTPException
from backend.app.schemas import EmbedRequest, EmbedResponse
from semantic.codebert.model import AdvancedCodeBERTEmbedder

router = APIRouter(prefix="/semantic", tags=["Semantic LLM Core"])

# Load frozen embedder globally for fast requests
# Uses mocking flag standard for non-GPU API envs if we need to mock
import os
use_mock = os.getenv("USE_MOCK_CODEBERT", "true").lower() == "true"

# Instantiate singleton embedding engine
class SemanticEngine:
    _instance = None
    @classmethod
    def get_embedder(cls):
        if cls._instance is None:
            # We fallback to basic embedder for fast mocking unless strictly required
            from feature_engineering.embeddings.codebert import CodeBERTEmbedder
            cls._instance = CodeBERTEmbedder(use_mock=use_mock)
        return cls._instance

@router.post("/embed", response_model=EmbedResponse, summary="Encode code string to 768-D vector")
async def embed_code(body: EmbedRequest):
    """Generates dense semantic tensors using CodeBERT."""
    if not body.code:
        raise HTTPException(400, "Provide at least one string of code.")
        
    try:
        embedder = SemanticEngine.get_embedder()
        
        # Output shape N x 768
        tensors = embedder.encode_batch(body.code)
        
        # Convert np back to lists for JSON
        res = tensors.tolist()
        
        return EmbedResponse(embeddings=res, dim=tensors.shape[1])
        
    except Exception as e:
        raise HTTPException(500, f"CodeBERT error: {str(e)}")
