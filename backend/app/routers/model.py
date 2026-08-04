# ============================================================
# Model Router — Async GNN Training and Inference
# ============================================================
# POST /api/v1/model/train   → queue a model training job
# GET  /api/v1/model/{id}    → check job status + metrics
# POST /api/v1/model/predict → run inference on a CPG
# ============================================================
from __future__ import annotations

import asyncio
import uuid
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import torch
import torch.nn as nn
from torch.optim import AdamW

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.config import get_settings
from backend.app.schemas import (
    TrainRequest,
    TrainJobResponse,
    TrainStatusResponse,
    PredictRequest,
    PredictResponse,
)
from models.gnn.architecture import VulnerabilityGAT
from models.datasets.datamodule import create_dataloaders
from models.training.trainer import train_epoch
from models.training.validator import valid_epoch
from models.training.tester import test_model
from models.training.inference import ModelInferenceService

import networkx as nx

router = APIRouter(prefix="/model", tags=["Model Training & Inference"])

# ── In-memory job store ─────
_train_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=1) # Limit to 1 for heavy GPU tasks usually

@router.post(
    "/train",
    response_model=TrainJobResponse,
    status_code=202,
    summary="Queue a GNN model training job",
)
async def queue_training_job(
    body: TrainRequest,
    background_tasks: BackgroundTasks,
) -> TrainJobResponse:
    settings = get_settings()
    job_id = uuid.uuid4()
    job_id_str = str(job_id)

    # Note: Using the dataset_job_id to find dataset directory
    # Normally we query DB for DatasetJob.dataset_path
    # For now, we assume standard layout
    # Try looking for .pt files in datasets/feature_tensors/
    dataset_dir = Path("./datasets/feature_tensors")
    
    # We will just pass the parent directory. create_dataloaders will glob it.
    if not dataset_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="No processed dataset directory found. Run feature engineering first."
        )

    # Create directories for outputs
    checkpoints_dir = Path("./checkpoints") / body.experiment_name
    metrics_dir = Path("./results/metrics") / body.experiment_name
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    _train_jobs[job_id_str] = {
        "job_id": job_id_str,
        "dataset_job_id": str(body.dataset_job_id),
        "experiment_name": body.experiment_name,
        "status": "queued",
        "started_at": datetime.now(timezone.utc),
    }

    background_tasks.add_task(
        _run_training_job,
        job_id_str=job_id_str,
        dataset_dir=dataset_dir,
        checkpoints_dir=checkpoints_dir,
        metrics_dir=metrics_dir,
        hyperparams=body.model_dump(),
    )

    return TrainJobResponse(
        training_job_id=job_id,
        dataset_job_id=body.dataset_job_id,
        status="queued",
        message="Training job queued. Poll GET /api/v1/model/{id}."
    )


@router.get(
    "/{job_id}",
    response_model=TrainStatusResponse,
    summary="Get training job status",
)
async def get_training_status(job_id: uuid.UUID) -> TrainStatusResponse:
    result = _train_jobs.get(str(job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Training job {job_id} not found.")

    return TrainStatusResponse(
        training_job_id=job_id,
        experiment_name=result.get("experiment_name", "unknown"),
        status=result.get("status", "unknown"),
        best_epoch=result.get("best_epoch", 0),
        best_val_f1=result.get("best_val_f1", 0.0),
        test_acc=result.get("test_acc", 0.0),
        test_f1=result.get("test_f1", 0.0),
        test_roc_auc=result.get("test_roc_auc", 0.0),
        checkpoint_path=result.get("checkpoint_path"),
        metrics_path=result.get("metrics_path"),
        error=result.get("error_message"),
        started_at=result.get("started_at"),
        completed_at=result.get("completed_at"),
    )

@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Run live inference on a parsed CPG graph",
)
async def predict_graph(body: PredictRequest) -> PredictResponse:
    settings = get_settings()
    cpg_job_id = str(body.cpg_job_id)
    
    graph_dir = settings.graphs_path if hasattr(settings, "graphs_path") else Path("./graphs")
    
    graph_json: Path | None = None
    for candidate in graph_dir.rglob("security_graph.json"):
        if cpg_job_id in str(candidate):
            graph_json = candidate
            break
            
    if not graph_json:
        # Fallback to pure graph.json if taint hasn't run
        for candidate in graph_dir.rglob("graph.json"):
            if cpg_job_id in str(candidate):
                graph_json = candidate
                break

    if not graph_json or not graph_json.exists():
        raise HTTPException(404, "Graph JSON not found for provided CPG Job ID")

    try:
        data = json.loads(graph_json.read_text(encoding="utf-8"))
        cpg = nx.DiGraph()
        for node in data.get("nodes", []):
            nid = node.pop("id")
            cpg.add_node(nid, **node)
        for edge in data.get("edges", []):
            src = edge.pop("source")
            tgt = edge.pop("target")
            cpg.add_edge(src, tgt, **edge)
            
        inference = ModelInferenceService(checkpoint_path=body.checkpoint_path)
        result = inference.predict(cpg)
        
        return PredictResponse(**result)
        
    except Exception as e:
        raise HTTPException(500, f"Inference failed: {str(e)}")


async def _run_training_job(
    job_id_str: str,
    dataset_dir: Path,
    checkpoints_dir: Path,
    metrics_dir: Path,
    hyperparams: dict,
) -> None:
    loop = asyncio.get_event_loop()
    
    _train_jobs[job_id_str]["status"] = "running"
    
    try:
        metrics = await loop.run_in_executor(
            _executor,
            _execute_training,
            dataset_dir,
            checkpoints_dir,
            metrics_dir,
            hyperparams
        )
        
        _train_jobs[job_id_str]["status"] = "completed"
        _train_jobs[job_id_str].update(metrics)
        _train_jobs[job_id_str]["completed_at"] = datetime.now(timezone.utc)
        
    except Exception as e:
        _train_jobs[job_id_str]["status"] = "failed"
        _train_jobs[job_id_str]["error_message"] = str(e)
        import traceback
        traceback.print_exc()
        _train_jobs[job_id_str]["completed_at"] = datetime.now(timezone.utc)

def _execute_training(
    dataset_dir: Path,
    checkpoints_dir: Path,
    metrics_dir: Path,
    kwargs: dict
) -> dict:
    
    # 1. Load Data
    train_dl, val_dl, test_dl = create_dataloaders(str(dataset_dir), batch_size=8)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = VulnerabilityGAT(
        hidden_channels=kwargs.get("hidden_dim", 128),
        heads=kwargs.get("heads", 4)
    ).to(device)
    
    # ── Imbalance Handling for Datasets like Big-Vul ──
    # Calculate pos_weight = total_negative / total_positive in training set
    total_pos = 0
    total_neg = 0
    for batch in train_dl:
        pos = int(batch.y.sum().item())
        total_pos += pos
        total_neg += (batch.y.size(0) - pos)
        
    pos_weight_val = total_neg / (total_pos + 1e-8)
    pos_weight = torch.tensor([pos_weight_val], device=device)
    
    optimizer = AdamW(model.parameters(), lr=kwargs.get("learning_rate", 0.001))
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    
    best_val_f1 = 0.0
    best_epoch = 0
    best_weights = None
    
    epochs = kwargs.get("epochs", 50)
    history = {"train_loss": [], "val_loss": [], "val_f1": []}
    
    # 2. Train Loop
    for epoch in range(1, epochs + 1):
        train_metrics = train_epoch(model, train_dl, optimizer, criterion, device)
        val_metrics = valid_epoch(model, val_dl, criterion, device)
        
        history["train_loss"].append(train_metrics["loss"])
        history["val_loss"].append(val_metrics["loss"])
        history["val_f1"].append(val_metrics["f1"])
        
        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            best_epoch = epoch
            best_weights = model.state_dict().copy()
            
            torch.save(best_weights, checkpoints_dir / "best_model.pt")

    # 3. Test final model
    if best_weights:
        model.load_state_dict(best_weights)
        
    test_metrics = test_model(model, test_dl, criterion, device)
    
    # Save training history
    with open(metrics_dir / "history.json", "w") as f:
        json.dump(history, f, indent=2)
        
    return {
        "best_epoch": best_epoch,
        "best_val_f1": best_val_f1,
        "test_acc": test_metrics.get("accuracy", 0),
        "test_f1": test_metrics.get("f1", 0),
        "test_roc_auc": test_metrics.get("roc_auc", 0),
        "checkpoint_path": str(checkpoints_dir / "best_model.pt"),
        "metrics_path": str(metrics_dir / "history.json"),
    }
