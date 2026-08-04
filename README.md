# Hybrid XAI Vulnerability Detection

> A research framework combining **Program Analysis** (Code Property Graphs, Taint Analysis) with **Graph Neural Networks** and **Explainable AI** for automated software vulnerability detection in C/C++ source code.

---

## Overview

This system takes raw C/C++ source code as input and produces:

1. **Vulnerability predictions** — Is this function vulnerable? What type of CWE?
2. **Explainable evidence** — Which code paths, nodes, and data flows contribute to the prediction?
3. **Interactive visualizations** — Zoomable graph views with highlighted attack paths and node attributions.

The pipeline fuses classical static analysis (taint tracking, control/data flow) with learned representations (GNN over CPG, CodeBERT embeddings) and explains its decisions using Captum-based attribution methods.

---

## Project Structure

```
hybrid-xai-vuln-detection/
├── backend/
│   ├── app/
│   ├── routes/
│   ├── services/
│   └── utils/
├── frontend/
│   ├── src/
│   ├── components/
│   └── pages/
├── parser/
│   ├── joern/
│   ├── preprocessing/
│   └── graph_builder/
├── taint_analysis/
├── feature_engineering/
├── models/
│   ├── gnn/
│   ├── embeddings/
│   └── training/
├── explainability/
├── visualization/
├── datasets/
├── experiments/
├── results/
├── tests/
├── docs/
├── papers/
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

### Why Each Folder Exists

#### `backend/` — REST API & Pipeline Orchestration

The FastAPI server that exposes every capability as an API endpoint. It accepts source code uploads, triggers the analysis pipeline, serves predictions, and returns explainability results to the frontend.

| Subfolder | Purpose |
|-----------|---------|
| `app/` | Application factory, startup/shutdown lifecycle, core configuration, middleware |
| `routes/` | API endpoint definitions grouped by domain (upload, analysis, prediction, reports) |
| `services/` | Business logic layer — each service orchestrates one pipeline stage (parsing, taint analysis, inference, explanation) |
| `utils/` | Shared helpers — file handling, response formatting, validation, logging utilities |

#### `frontend/` — Interactive Web Dashboard

A React + Vite single-page application that provides the user interface for uploading code, viewing vulnerability reports, and interacting with graph visualizations.

| Subfolder | Purpose |
|-----------|---------|
| `src/` | Application entry point, routing setup, global styles, API client configuration |
| `components/` | Reusable UI building blocks — graph viewer, code panels, metric cards, modals |
| `pages/` | Full page views — Dashboard, Upload, Graph Explorer, Explanation View, Reports, Settings |

#### `parser/` — Source Code → Graph Transformation

Converts raw C/C++ source files into structured graph representations (Code Property Graphs) that combine Abstract Syntax Trees, Control Flow Graphs, and Program Dependency Graphs.

| Subfolder | Purpose |
|-----------|---------|
| `joern/` | Joern CLI integration — wrapper scripts, Joern query definitions (`.sc` files), CPG export logic |
| `preprocessing/` | Code tokenization, normalization, function extraction, dataset cleaning pipelines |
| `graph_builder/` | Constructs NetworkX / PyG-compatible graph objects from Joern's raw output (nodes, edges, properties) |

#### `taint_analysis/` — Data Flow Security Analysis

Implements source-to-sink taint tracking over the CPG. Identifies untrusted data sources (e.g., `recv`, `scanf`), sensitive sinks (e.g., `memcpy`, `strcpy`), propagation rules, and sanitization points. Produces **attack paths** — ordered sequences of nodes/edges from source to sink where unsanitized data flows.

#### `feature_engineering/` — Graph Feature Extraction

Transforms raw graph structures into numerical feature tensors suitable for GNN input. Extracts:

- **Node features** — AST node type, code token embeddings, taint labels, call depth, in/out degree
- **Edge features** — Edge type encoding (AST/CFG/DFG/call), data dependency flags
- **Graph-level features** — Cyclomatic complexity, function metrics, number of sources/sinks
- **Semantic features** — CodeBERT embeddings fused with structural features

#### `models/` — Deep Learning Models

Houses all neural network architectures, embedding generators, and training infrastructure.

| Subfolder | Purpose |
|-----------|---------|
| `gnn/` | GNN architecture definitions — GCN, GAT, GraphSAGE, GIN, and hybrid models |
| `embeddings/` | CodeBERT / GraphCodeBERT integration, embedding extraction, caching |
| `training/` | Training loops, evaluation scripts, hyperparameter configs, checkpointing, TensorBoard logging |

#### `explainability/` — XAI Attribution Methods

Implements multiple explainability techniques to answer *why* the model flagged a function as vulnerable:

- **Integrated Gradients** — Gradient-based node/feature attribution via Captum
- **GNNExplainer** — Learns an edge mask that identifies the most influential subgraph
- **SubGraphX** — Identifies minimal subgraphs sufficient for the prediction
- **SHAP/LIME** — Model-agnostic perturbation-based explanations

Produces node importance scores, critical subgraphs, and natural language vulnerability descriptions.

#### `visualization/` — Graph Rendering & Export

Server-side graph rendering utilities — generates static visualizations (PNG/SVG/PDF) of attributed graphs, attack paths, and comparison plots. Complements the frontend's interactive Cytoscape.js views.

#### `datasets/` — Benchmark Data

Stores raw and preprocessed vulnerability datasets (Big-Vul, Devign, SARD, D2A). Large files are Git-ignored; use DVC or manual download scripts. See [`datasets/README.md`](datasets/README.md) for details.

#### `experiments/` — Experiment Configurations

Jupyter notebooks, YAML/JSON experiment configs, and scripts for running ablation studies, hyperparameter sweeps, and model comparisons. Each experiment is reproducible via a config file + random seed.

#### `results/` — Outputs & Metrics

Stores evaluation outputs: metric tables (accuracy, precision, recall, F1), confusion matrices, ROC curves, comparison charts, and per-experiment logs. Git-ignored for large binary outputs.

#### `tests/` — Test Suite

Unit tests, integration tests, and end-to-end pipeline tests. Organized to mirror the source tree (e.g., `tests/parser/`, `tests/models/`).

#### `docs/` — Documentation

Architecture documents, API specs, database schemas, deployment guides. See [`docs/README.md`](docs/README.md) for the planned documentation index.

#### `papers/` — Reference Literature

Research papers, survey articles, and notes relevant to the project. Organized by topic area. See [`papers/README.md`](papers/README.md).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy 2.0, PostgreSQL, Alembic |
| **Frontend** | React 18, Vite, Tailwind CSS, Cytoscape.js, Recharts |
| **ML Framework** | PyTorch, PyTorch Geometric |
| **Code Embeddings** | CodeBERT / GraphCodeBERT (HuggingFace Transformers) |
| **Explainability** | Captum, SHAP |
| **Parser** | Joern (CPG generation), NetworkX |
| **Dev Tools** | Ruff, MyPy, Pytest, Pre-commit |

---

## Quick Start

### Prerequisites

- Python ≥ 3.10
- Node.js ≥ 18
- PostgreSQL ≥ 14
- [Joern](https://joern.io) CLI installed
- (Optional) CUDA-capable GPU for model training

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/kunal/hybrid-xai-vuln-detection.git
cd hybrid-xai-vuln-detection

# 2. Create Python virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -e ".[dev,notebooks]"
# or: pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials, Joern path, etc.

# 5. Install frontend dependencies
cd frontend && npm install && cd ..

# 6. Start development servers
# Terminal 1 — Backend
uvicorn backend.app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

---

## Development Roadmap

This project is built incrementally across 10 phases / 28 steps. See the [implementation plan](docs/architecture.md) for full details.

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Project Foundation | ✅ Complete |
| 1 | Parser Module | ⬜ Pending |
| 2 | Taint Analysis | ⬜ Pending |
| 3 | Feature Engineering | ⬜ Pending |
| 4 | GNN Model | ⬜ Pending |
| 5 | CodeBERT Integration | ⬜ Pending |
| 6 | Explainability (XAI) | ⬜ Pending |
| 7 | Backend API | ⬜ Pending |
| 8 | Frontend Dashboard | ⬜ Pending |
| 9 | End-to-End Integration | ⬜ Pending |
| 10 | Research & Experiments | ⬜ Pending |

---

## License

MIT

---

*Built as part of the Hybrid XAI Vulnerability Detection research project.*
