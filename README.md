# VulnScan

**AI-assisted software vulnerability detection, explainability, and remediation.**

VulnScan is a security analysis platform for detecting, investigating, explaining, remediating, and verifying software vulnerabilities. It combines deterministic program analysis (AST, CFG, CPG, call graphs, taint analysis) with AI-assisted detection, explainable AI (XAI), remediation generation, patch validation, and verification scans.

> Security findings must be evidence-driven and verifiable. AI assists the workflow; it does not replace authoritative security state.

## Table of Contents

- [Overview](#overview)
- [Why VulnScan](#why-vulnscan)
- [Architecture](#architecture)
- [End-to-End Workflow](#end-to-end-workflow)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Testing](#testing)
- [Security Model](#security-model)
- [Analysis Boundary](#analysis-boundary)
- [AI Provider Architecture](#ai-provider-architecture)
- [Design Principles](#design-principles)
- [Documentation](#documentation)
- [Project Status](#project-status)
- [Responsible Use](#responsible-use)
- [License](#license)

---

## Overview

VulnScan provides an end-to-end workflow for analyzing source code and turning security findings into actionable, verifiable remediation.

Core capabilities:

- Multi-tenant organizations and role-based access control (RBAC)
- Project and repository management
- Immutable source snapshots
- Source preprocessing and function extraction
- Static program analysis (AST, CFG, CPG, PDG, call graph, where supported)
- Data-flow and taint analysis
- AI-assisted vulnerability detection
- CWE classification, severity, and CVSS information
- Finding correlation and deduplication
- Explainable AI with evidence-aware explanations
- AI-assisted remediation
- Patch validation, regression detection, and verification scans
- Security reports and analytics
- Security gates, GitHub and CI integration
- Notifications and audit logging
- Tenant isolation
- Operational health and observability

---

## Why VulnScan

Traditional static analysis can flag suspicious code patterns, but it often gives developers too much low-level information and too little context. AI systems can add useful semantic reasoning, but their output must not become an unchecked source of security truth.

VulnScan combines both approaches:

```text
Source Code
    │
    ▼
Immutable Source Snapshot
    │
    ▼
Preprocessing
    ├── Language Detection
    ├── Function Extraction
    ├── Tokenization
    └── Normalization
    │
    ▼
Static Analysis
    ├── AST
    ├── CFG
    ├── CPG
    ├── Call Graph
    └── Data / Taint Analysis
    │
    ▼
AI Analysis
    ├── Semantic Representation
    ├── Graph Representation
    ├── Vulnerability Detection
    ├── CWE Classification
    └── Severity / CVSS
    │
    ▼
Evidence Correlation
    ├── Static Evidence
    ├── Taint Evidence
    ├── Graph Evidence
    └── AI Evidence
    │
    ▼
Finding
    ├── Explain
    ├── Remediate
    ├── Validate
    └── Verify
    │
    ▼
Security Result
```

---

## Architecture

VulnScan is a modular full-stack system.

```text
                     Web Frontend
                    React + Vite
                          │
                          │ HTTP / WebSocket
                          ▼
                  ┌─────────────────┐
                  │     FastAPI     │
                  │    REST API     │
                  │   Auth / RBAC   │
                  │ Tenant Control  │
                  └────────┬────────┘
                           │
            ┌──────────────┼───────────────┐
            ▼              ▼               ▼
       PostgreSQL        Redis        Object Storage
        Metadata      Queue / State   Source / Artifacts
            │              │               │
            └──────────────┼───────────────┘
                           ▼
                    Celery Workers
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
   Preprocessing     Static Analysis    Scan Pipeline
                       ├── AST
                       ├── CFG
                       ├── CPG
                       ├── Call Graph
                       └── Taint
                           │
                           ▼
                      AI Adapters
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Graph Models  Semantic Models  Fusion Layer
              └────────────┼────────────┘
                           ▼
                     AI Predictions
                           │
                           ▼
                   Finding Correlation
                           │
                           ▼
                        Findings
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
             XAI      Remediation    Reporting
                           │
                           ▼
                    Patch Validation
                           │
                           ▼
                    Verification Scan
                           │
                           ▼
                  Verified Security State
```

More detail:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/SYSTEM_FLOW.md`](docs/SYSTEM_FLOW.md)
- [`docs/SCANNING_PIPELINE.md`](docs/SCANNING_PIPELINE.md)
- [`docs/REMEDIATION.md`](docs/REMEDIATION.md)

---

## End-to-End Workflow

```text
User
 │
 ▼
Organization
 │
 ▼
Project
 │
 ▼
Repository
 │
 ▼
Immutable Source Snapshot
 │
 ▼
Scan
 ├── Queue
 ├── Preprocess
 ├── Static Analysis
 ├── Graph Analysis
 ├── Taint Analysis
 └── AI Analysis
 │
 ▼
Finding Correlation
 │
 ▼
Finding
 ├── Evidence
 ├── CWE
 ├── Severity
 ├── CVSS
 └── Risk
 │
 ▼
Investigation
 ├── Source
 ├── Static Evidence
 ├── Taint Evidence
 ├── Graph Evidence
 └── AI Explanation
 │
 ▼
Remediation
 ├── Proposed Fix
 ├── Human Review
 └── Patch
 │
 ▼
Validation
 ├── Patch Application
 ├── Syntax
 ├── Tests
 ├── Static Analysis
 ├── Taint / Graph Checks
 └── Regression Checks
 │
 ▼
Verification Scan
 │
 ▼
Finding Lifecycle
 ├── FIXED
 └── VERIFIED
 │
 ▼
Reports / Analytics / CI Security Gate
```

The key architectural rule: **AI-generated output never directly becomes verified security state.** A remediation must pass validation and verification before a finding can reach a verified state.

---

## Features

### 1. Multi-Tenancy and RBAC

VulnScan is organization-aware. An organization contains users, members, roles, permissions, projects, repositories, scans, findings, reports, and security policies.

Authorization is enforced at the API layer through canonical roles and centralized permission checks. Tenant boundaries are enforced so that a resource belonging to one organization cannot be accessed through another organization's context.

### 2. Source Ingestion

Source code can be ingested through supported repository and upload workflows. Ingestion produces an immutable source snapshot.

```text
Repository / Upload
        │
        ▼
Source Snapshot
        ├── Source Files
        ├── Functions
        ├── Manifest
        └── Integrity Metadata
```

The original source is preserved. Analysis and preprocessing never overwrite the authoritative snapshot.

### 3. Preprocessing

Before analysis, VulnScan prepares source code for downstream processing:

- Language detection
- Source validation
- Function extraction
- Tokenization
- Identifier normalization
- Optional comment handling
- Duplicate-function detection
- Function metadata
- Source integrity information

Preprocessing is deterministic wherever possible.

### 4. Static Analysis

Static analysis provides deterministic program evidence. Depending on the configured analysis engine, VulnScan can work with:

- AST
- CFG
- CPG
- PDG (where supported)
- Call graph
- Data flow
- Pointer analysis
- Taint analysis
- Complexity information
- API usage information

Graph artifacts carry explicit metadata: source snapshot, graph type, schema version, artifact location, checksum, node count, and edge count.

Unsupported analysis is reported as unsupported. It is never represented as fabricated evidence.

### 5. Taint Analysis

Taint analysis tracks potentially dangerous data flows.

```text
Source
  │
  ▼
Input
  │
  ▼
Propagation
  ├── Sanitizer
  └── Unsafe Flow
          │
          ▼
         Sink
```

Taint results are treated as static evidence. A detected taint path does not by itself confirm a vulnerability.

### 6. AI Analysis

AI inference is isolated behind provider contracts, so the rest of the platform is not coupled to a specific model.

```text
               AIInferenceProvider
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
  Vulnerability      CWE         Severity
    Detection      Provider      Provider
        └─────────────┼─────────────┘
                      ▼
                 AIPrediction
```

Potential model components:

- Graph neural networks
- GraphCodeBERT / CodeBERT-family semantic models
- Graph encoders and semantic encoders
- Fusion layers
- Vulnerability classifiers
- CWE classifiers
- Severity / CVSS predictors

The provider boundary lets trained models be introduced without rewriting the scan, finding, API, or frontend layers.

### 7. Finding Correlation

VulnScan does not treat every signal as an independent vulnerability. The finding engine combines evidence from static analysis, graph analysis, taint analysis, AI predictions, source location, CWE, severity, confidence, and risk information into a single canonical, persistent finding.

Repeated scans are correlated using finding fingerprints, so the same vulnerability does not become a new finding each time a project is scanned.

### 8. Finding Lifecycle

Findings follow a controlled lifecycle. The typical progression:

```text
OPEN
  │
  ▼
CONFIRMED
  │
  ▼
IN_PROGRESS
  │
  ▼
FIX_PROPOSED
  │
  ▼
UNDER_REVIEW
  │
  ▼
FIXED
  │
  ▼
VERIFIED
```

Alternative states:

- `FALSE_POSITIVE`
- `RISK_ACCEPTED`
- `SUPPRESSED`
- `REOPENED`

State changes are controlled by backend services and authorization rules.

### 9. Explainable AI

XAI is a technical capability of VulnScan. The explanation architecture can include:

- Integrated Gradients
- SHAP
- GNNExplainer
- Attention-based attribution
- Graph, node, and edge attribution
- Token-level attribution

The explanation layer is evidence-aware. It keeps deterministic evidence, AI evidence, and the explanation itself distinct, rather than presenting an AI-generated explanation as independent proof.

### 10. Remediation

VulnScan can generate remediation proposals for findings. The remediation workflow is separate from the finding lifecycle.

```text
Finding
   │
   ▼
Explanation Context
   │
   ▼
Remediation Provider
   │
   ▼
Proposed Patch
   │
   ▼
Human Review
   │
   ▼
Patch Application
   │
   ▼
Validation
```

AI-generated patches remain untrusted until validated.

### 11. Patch Validation

Patch validation runs outside the main API process, using disposable workspaces and bounded execution. Validation can include:

1. Patch application
2. Syntax validation
3. Build and test execution
4. Static analysis
5. Graph and taint analysis
6. Regression checks
7. Final verification

The validation environment is designed to keep application secrets away from executed code. Kernel-level isolation depends on the deployment environment.

### 12. Verification

A successful patch validation is not equivalent to a verified security fix. VulnScan runs a verification scan against the modified state.

```text
Original Finding
      │
      ▼
Proposed Patch
      │
      ▼
Patch Validation
      │
      ▼
Verification Scan
      ├── Finding still present ──► REOPEN
      └── Finding resolved ───────► VERIFIED
```

This keeps three things separate: the AI suggestion, the patch validation, and the security verification.

### 13. Reports and Analytics

Reports and analytics are built from authoritative persisted security data. Reports can include findings, severity, CWE, scan, project, and remediation information, as well as security gate results.

Supported formats: PDF, HTML, JSON, CSV.

### 14. CI/CD and GitHub Integration

```text
Pull Request
     │
     ▼
GitHub Webhook
     │
     ▼
Repository / Project Resolution
     │
     ▼
Source Snapshot
     │
     ▼
Incremental Scan
     │
     ▼
Finding Comparison
     ├── Existing
     ├── New
     └── Fixed
     │
     ▼
Security Gate
     ├── PASS
     └── FAIL
```

Security gate policies can evaluate conditions such as new Critical findings, new High findings, secret-related findings, and CVSS thresholds. Webhook requests are authenticated and protected against replay.

### 15. Security Architecture

**Authentication**

- Account authentication
- Session lifecycle
- Refresh token rotation
- Session revocation
- Password recovery
- Verification workflows
- API keys

**Authorization**

Centralized around organization membership, roles, permissions, resource ownership, and tenant boundaries.

**Source safety**

Uploaded source is treated as untrusted. Protections include:

- Archive traversal protection
- Absolute path, Windows path, and UNC path protection
- Null-byte protection
- Archive size and file-count limits
- Extraction controls
- Disposable analysis workspaces

**AI safety**

AI output is treated as untrusted and cannot independently establish a verified security state.

**Model integrity**

Model artifacts can be verified through checksums. Tampered or missing artifacts fail closed where integrity verification is required.

**Webhook security**

- HMAC verification
- Constant-time signature comparison
- Delivery deduplication
- Replay handling
- Conflicting replay detection

### 16. Reliability and Observability

The scan system tracks scan state, stage state, heartbeats, failures, cancellation, timeouts, and worker activity. Stale scans are detected and moved out of permanently running states.

Health endpoints expose dependency status for PostgreSQL, Redis, object storage, and Celery workers. Operational metrics include API and scan counters and duration measurements. Request IDs support request correlation.

---

## Technology Stack

| Layer                 | Technology                            |
| --------------------- | ------------------------------------- |
| Frontend              | React                                 |
| Frontend build        | Vite                                  |
| Backend               | FastAPI (Python)                      |
| Database              | PostgreSQL                            |
| Queue / cache         | Redis                                 |
| Background processing | Celery                                |
| Object storage        | S3-compatible storage / MinIO         |
| Static analysis       | Native analysis + Joern integration   |
| Graph processing      | Graph-based analysis pipeline         |
| AI                    | PyTorch / model-provider architecture |
| Graph ML              | PyTorch Geometric / GNN architecture  |
| Explainability        | Captum / XAI adapters                 |
| Authentication        | Token / session-based                 |
| Migrations            | Alembic                               |
| Testing               | Pytest / Vitest                       |
| Containers            | Docker / Docker Compose               |

---

## Repository Structure

```text
VulnScan/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai_inference/
│   │   │   ├── finding_service/
│   │   │   ├── scan_pipeline/
│   │   │   ├── xai/
│   │   │   ├── remediation/
│   │   │   ├── reporting/
│   │   │   └── ...
│   │   └── main.py
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── stores/
│       └── ...
├── cli/
├── docs/
├── scripts/
├── .github/
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── ...
```

For a detailed codebase map, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Local Development

### Prerequisites

- Python
- Node.js
- PostgreSQL
- Redis
- Docker / Docker Compose

Some analysis and AI capabilities also require their own runtimes or model artifacts.

### Start the platform

```bash
docker compose up --build
```

Check running services:

```bash
docker compose ps
```

Frontend and backend URLs and environment setup are documented in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) and [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

---

## Configuration

Configuration is environment-driven. Start from:

```text
.env.example
backend/.env.example
frontend/.env.example
```

Never commit production secrets, API keys, private credentials, model credentials, webhook secrets, database passwords, or generated security artifacts.

Full reference: [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md).

---

## Testing

**Backend**

```bash
python -m pytest backend/tests/
```

**Frontend**

```bash
npm test -- --run
```

**Production build**

```bash
npm run build
```

Test coverage includes authentication, RBAC, tenant isolation, source ingestion, scan lifecycle, static analysis, taint analysis, AI provider boundaries, finding correlation, XAI, remediation, validation, verification, reports, analytics, GitHub security gates, webhook security, reliability, rate limiting, performance, and repository integrity.

---

## Security Model

- **Tenant isolation:** every organization-owned resource stays scoped to its organization.
- **Least privilege:** users receive only the permissions their role requires.
- **Immutable evidence:** source snapshots and security evidence are preserved, not silently overwritten.
- **AI is untrusted:** AI output is advisory until validated by authoritative application logic.
- **Fail closed:** security-sensitive integrity checks fail closed when required information is missing or invalid.
- **Explicit uncertainty:** unsupported analysis and unavailable providers are reported as such, never replaced with fabricated results.
- **Disposable execution:** untrusted code runs in bounded, disposable workspaces, not inside the primary API process.

---

## Analysis Boundary

VulnScan has a native analysis path and can integrate with external analysis infrastructure such as Joern. When an advanced external capability is unavailable, the platform reports that accurately using distinct states:

```text
Available
Unsupported
Unavailable
Failed
Not Run
```

These states are intentionally different. The platform never represents an unavailable analysis engine as if it had produced real security evidence.

---

## AI Provider Architecture

AI capabilities sit behind provider interfaces, so the system can move from development providers to trained models without rewriting the rest of VulnScan.

```text
                VulnScan AI Boundary
                        │
                        ▼
                AI Provider Interface
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     Development    Local Torch    External
      Provider       Provider      Provider
          └─────────────┼─────────────┘
                        ▼
                 Canonical Output
                        │
                        ▼
                Finding Correlation
```

Model versions and provenance are tracked independently from the finding domain.

---

## Design Principles

- **Evidence over appearance:** a finding must be backed by traceable evidence.
- **Deterministic state over AI authority:** AI assists but never determines verified security state.
- **Immutable source:** scans reference immutable source snapshots.
- **Explicit lifecycle:** scans, findings, remediation, and validation each have controlled lifecycle states.
- **Tenant isolation by design:** organization scope is enforced throughout the backend.
- **Provider abstraction:** models and external providers can change without rewriting the domain layer.
- **Truthful system state:** unsupported, unavailable, failed, and not-run states are explicit.
- **Bounded execution:** long-running and untrusted operations are isolated from request handling.
- **Human review:** remediation is reviewable before it becomes authoritative.

---

## Documentation

| Document                                       | Purpose                                       |
| ---------------------------------------------- | --------------------------------------------- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Detailed system and code architecture         |
| [`docs/SYSTEM_FLOW.md`](docs/SYSTEM_FLOW.md)   | End-to-end explanation of how VulnScan works  |
| [`docs/SCANNING_PIPELINE.md`](docs/SCANNING_PIPELINE.md) | Scan lifecycle and analysis pipeline |
| [`docs/REMEDIATION.md`](docs/REMEDIATION.md)   | XAI, remediation, validation, verification    |
| [`docs/AI_AND_MODELS.md`](docs/AI_AND_MODELS.md) | AI provider and model architecture          |
| [`docs/API.md`](docs/API.md)                   | API organization and contracts                |
| [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) | Environment and configuration reference     |
| [`docs/SECURITY.md`](docs/SECURITY.md)         | Security architecture                         |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)   | Local development workflow                    |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)     | Deployment and operational guidance           |

---

## Project Status

VulnScan currently provides the core end-to-end platform architecture, from organization and project management through immutable snapshots, scanning, static/graph/taint analysis, the AI inference boundary, finding correlation, XAI explanations, remediation, patch validation, verification scans, and reports, analytics, and CI security gates.

The architecture is designed so that trained models and production infrastructure can be integrated behind the existing boundaries without a platform rewrite.

---

## Responsible Use

VulnScan is intended for authorized software and repository analysis. Only scan source code and systems you have permission to analyze.

Review security findings in their source and deployment context before acting on them. Treat AI-generated explanations and remediation proposals as assistance, not as unquestionable security truth.

---

## License

See [`LICENSE`](LICENSE) for licensing information.

---

**VulnScan's core objective:** detect the vulnerability, explain the evidence, assist the fix, validate the change, and verify the result.