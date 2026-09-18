# Hybrid XAI Vulnerability Detection Platform

> A production-grade security platform combining **Program Analysis** (Code Property Graphs, Taint Analysis) with **Graph Neural Networks** and **Explainable AI (XAI)** for automated software vulnerability detection in C/C++ source code.

---

## Architecture Overview (Phase 1 Foundation)

```
                       ┌─────────────────────────┐
                       │     React 18 + Vite     │
                       │ (TypeScript + Tailwind) │
                       └────────────┬────────────┘
                                    │ Canonical API Client
                                    ▼
                       ┌─────────────────────────┐
                       │      FastAPI Backend    │
                       │  (Routers, Services,    │
                       │   Repositories, Guards) │
                       └─────┬──────┬──────┬─────┘
                             │      │      │
              ┌──────────────┘      │      └──────────────┐
              ▼                     ▼                     ▼
     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
     │   PostgreSQL    │   │      Redis      │   │ Storage Service │
     │  (SQLAlchemy 2  │   │  (Celery Broker │   │ (Hardened Local │
     │   + Alembic)    │   │  + Cache Store) │   │   Path / S3)    │
     └─────────────────┘   └────────┬────────┘   └─────────────────┘
                                    │
                                    ▼
                           ┌─────────────────┐
                           │  Celery Worker  │
                           │ Infrastructure  │
                           └─────────────────┘
```

> **Note on Phase 1 Scope**: Phase 1 establishes the engineering, security, database migration, API, shared UI, and infrastructure foundation. In accordance with the project architecture roadmap, the actual scanning engine (Joern CPG extraction, AI model inference, and patch validation) is deferred to Phases 4–6.

---

## Key Security Foundations Implemented (Phase 1)

1. **Admin Self-Registration Blocked**: Registration schemas and services strictly reject elevated roles (`admin`, `owner`, `security_lead`). Public registrations default exclusively to standard roles (`security_analyst`, `developer`).
2. **Path Traversal & Zip-Slip Hardening**: Upload handling utilizes UUID-generated paths (`upload_id/filename.ext`). Archive extraction rigorously validates member paths against `..`, absolute paths, Windows drive specifiers (`C:`), UNC paths (`\\`), and symlink escapes.
3. **Archive Resource Limits**: Enforces strict configurable thresholds on max upload size (100MB), max extraction size (500MB), and max member files (1,000) to prevent decompression bombs.
4. **Database Migration Authority**: Removed `Base.metadata.create_all()` from runtime startup; schema definition is managed authoritatively via Alembic migrations.
5. **Session Isolation**: Frontend token management is encapsulated behind a unified `authStorage` abstraction, preventing arbitrary `localStorage` access across UI components.

---

## Quickstart — Running with Docker Compose

The complete environment (PostgreSQL, Redis, FastAPI backend, Celery worker, and Vite frontend) can be launched with Docker Compose:

```bash
# 1. Copy the environment configuration
cp .env.example .env

# 2. Start all services
docker compose up -d

# 3. View logs
docker compose logs -f
```

Services are exposed on:
- **Frontend Dashboard**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Checks**: `http://localhost:8000/health` and `http://localhost:8000/health/ready`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

---

## Running Locally for Development

### 1. Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- PostgreSQL 15+
- Redis 7+

### 2. Environment Setup
```bash
cp .env.example .env
# Adjust DATABASE_URL, REDIS_URL, and SECRET_KEY as appropriate
```

### 3. Backend Setup & Migrations
```bash
# Set up Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run Alembic database migrations
cd backend
alembic upgrade head
cd ..

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```

### 4. Celery Worker
```bash
# From workspace root with activated venv:
celery -A backend.app.workers.celery_app.celery_app worker --loglevel=info
```

### 5. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## Testing

### Backend Tests (pytest)
Runs API security, authentication, Zip-Slip, storage isolation, and health endpoint tests:
```bash
# From workspace root:
pytest backend/tests -v
```

### Frontend Tests (Vitest)
Runs UI primitives and authentication boundary unit tests:
```bash
# From frontend directory:
cd frontend
npm test
```

### Production Build Validation
```bash
cd frontend
npm run build
```

---

## Phase Roadmap Status

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 0** | Architecture Specification & Domain Design | **Completed & Frozen** |
| **Phase 1** | Foundation & Existing Codebase Reconstruction | **Completed** |
| **Phase 2** | Organization Context, RBAC & Multi-tenancy | Next |
| **Phase 3** | Source Ingestion, Snapshots & Preprocessing | Deferred |
| **Phase 4** | Joern CPG Extraction & Celery Orchestration | Deferred |
| **Phase 5** | AI Ingestion, GNN/CodeBERT Inference & Findings | Deferred |
| **Phase 6** | Explainable AI (Captum) & Remediation Verification | Deferred |
| **Phase 7** | Reports, Analytics & CI/CD Integrations | Deferred |
| **Phase 8** | Platform Hardening, Reliability & Full E2E | Deferred |

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

## Phase 3 Architecture: Source Ingestion, Provenance & Preprocessing

```
                   ┌─────────────────────────────────────────────────┐
                   │             Ingestion Entrypoints               │
                   │   ZIP Upload │ Files Upload │ Git │ GitHub      │
                   └────────────────────────┬────────────────────────┘
                                            │
                                            ▼
                   ┌─────────────────────────────────────────────────┐
                   │               FastAPI API Layer                 │
                   │  - Authenticate & enforce Org/Project RBAC      │
                   │  - Stream raw artifact to Object Storage        │
                   │  - Persist pending SourceSnapshot metadata      │
                   │  - Enqueue job into Celery default_queue        │
                   └────────────────────────┬────────────────────────┘
                                            │
                                            ▼
                   ┌─────────────────────────────────────────────────┐
                   │             Isolated Celery Worker              │
                   │  - Unique ephemeral scratch directory           │
                   │  - Safe zip extraction (no Zip-Slip / symlinks) │
                   │  - File classification (source, noise, binary)  │
                   │  - Language detection (extension + heuristics)  │
                   │  - AST & syntax function extraction             │
                   │  - Deterministic tokenization & normalization   │
                   │  - Semantic clone duplicate grouping            │
                   │  - Generate & store JSON manifest in S3         │
                   │  - Mark SourceSnapshot as READY                 │
                   └────────────────────────┬────────────────────────┘
                                            │
                         ┌──────────────────┴──────────────────┐
                         ▼                                     ▼
        ┌──────────────────────────────────┐  ┌──────────────────────────────────┐
        │       PostgreSQL Metadata        │  │       S3 / MinIO Storage         │
        │ - Projects & Repositories        │  │ - Original source code artifacts │
        │ - RepositoryCommits (SHA)        │  │ - Normalized code representations│
        │ - SourceSnapshots (Immutable)    │  │ - Token stream artifacts         │
        │ - SourceFiles & Extracted Funcs  │  │ - Reproducible snapshot manifests│
        └──────────────────────────────────┘  └──────────────────────────────────┘
```

---

## Phase 4–6 Architecture: Complete Detection, Correlation, XAI & Remediation Pipeline

```
SourceSnapshot (Immutable)
    ↓
Static Analysis Pipeline (AST / CFG / PDG / CPG / CallGraph)
    ↓
Taint Analysis Engine (Source → Sink Data-flow Tracking)
    ↓
AI Inference Provider (LocalTorchProvider / Boundary Factory)
    ↓
Canonical AIPrediction (Fingerprinted & Scored)
    ↓
Correlation Engine (Cross-scan Deduplication & Occurrence Tracking)
    ↓
Finding (Persistent Domain Model)
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Explainability & XAI Engine                                 │
│ - Evidence-Aware Context Synthesis                         │
│ - Normalized Attribution (Captum IG, SHAP, GNNExplainer, Attn)│
│ - Important Source Lines, Attributed Tokens, Graph Nodes    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Remediation Engine                                          │
│ - Proposed Unified Diff Patch with SHA-256 Checksum        │
│ - Path Sanitization (Rejects .. & absolute paths)           │
│ - Human Review (APPROVE / REJECT)                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Disposable Validation Sandbox (/tmp/validation_workspaces/)  │
│ 1. Patch Apply (Verified Checksum & Base Snapshot)          │
│ 2. Syntax Validation (compileall / node --check)            │
│ 3. Build & Test Execution (Allowlisted, Zero Secrets)        │
│ 4. Static Re-Analysis (Re-evaluates Original Finding)       │
│ 5. Taint & Graph Re-Analysis                                │
│ 6. Security Regression Check (Detects Introduced Flaws)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ Authoritative Verification Scan                             │
│ - Trigger: SYSTEM_RESCAN (purpose=REMEDIATION_VERIFICATION) │
│ - Verifies original vulnerability fingerprint is absent     │
│ - Transitions finding: FIXED → VERIFIED                     │
│ - Invariant: AI-generated fix != verified fix               │
└─────────────────────────────────────────────────────────────┘
```

### Core Security & Architectural Invariants

1. **AI-Generated Fix != Verified Fix**: An AI model, LLM, or patch generator can never set a finding's status to `FIXED` or `VERIFIED`. Only the authoritative `FindingLifecycleService` can execute this transition after the multi-stage validation sandbox and verification scan prove resolution with persisted evidence.
2. **Disposable Validation Sandboxing**: Untrusted patch execution occurs inside disposable validation workspaces (`/tmp/validation_workspaces/<validation_id>`). Environment variables containing database passwords, API keys, and cloud credentials are intentionally stripped.
3. **Strict Path Sanitization**: Proposed patches are scanned prior to application; patches containing directory traversal (`..`), absolute paths, or references outside the sandbox are rejected with `PatchSecurityError`.
4. **Source Snapshot Immutability**: Base source code snapshots are read-only and cryptographically hashed. Applying a patch never modifies the base snapshot.
5. **Deduplication & Regression Reopening**: Findings persist across scans via stable SHA-256 fingerprints. If a vulnerability previously marked `VERIFIED` is re-detected in a subsequent scan, it automatically transitions to `REOPENED` with a new `FindingOccurrence` while preserving historical `VERIFIED` audit records.
6. **Zero Fake Results**: If PyTorch model checkpoints, GPU devices, or GNN weights are unconfigured, providers return structured `MODEL_NOT_READY` or `NOT_SUPPORTED` error boundaries. The system never fabricates attribution scores or synthetic passes.

---

## Development Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Project Architecture & Specifications | ✅ Complete |
| 1 | Infrastructure, Auth Baseline, Security Hardening | ✅ Complete |
| 2 | Multi-Tenancy, Organizations, Custom RBAC & Audit | ✅ Complete |
| 3 | Project, Repository, Source Ingestion & Preprocessing | ✅ Complete |
| 4 | Code Property Graph (CPG) Construction, Static Analysis & Taint Pipeline | ✅ Complete |
| 5 | AI Provider Boundary, Finding Deduplication, Correlation & Results Workspace | ✅ Complete |
| 6 | Explainable AI (XAI), LLM Remediation, Sandbox Validation & Verification Scan | ✅ Complete |
| 7 | Security Reports, Export Engine (PDF/HTML) & CI/CD Integrations | ⬜ Deferred |
| 8 | Production Hardening, Distributed HA Clusters & Enterprise SSO | ⬜ Deferred |

---

## License

MIT

---

*Built as part of the Hybrid XAI Vulnerability Detection research project.*

