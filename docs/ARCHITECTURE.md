# Codebase Architecture Map (Phase 1 Foundation)

This document establishes the architecture baseline for the Hybrid XAI Vulnerability Detection platform as reconstructed in Phase 1. It details the runtime layers, structural boundaries, storage abstraction, security posture, and the explicitly deferred Phase 2–8 capabilities.

---

## 1. System Overview

```
                        FRONTEND (React 18 + TypeScript + Vite)
                                          ↕
                             CANONICAL API CLIENT (Axios)
                                          ↕
                             FASTAPI BACKEND (Python 3.11+)
                                          ↕
         ┌────────────────────────┬───────┴────────────────────────┬────────────────────────┐
         ↓                        ↓                                ↓                        ↓
    PostgreSQL                 Redis                      Storage Abstraction            Celery
  (Alembic Migrations)   (Broker & Result Cache)      (Local Dev / MinIO S3)       (Worker Tasks)
```

---

## 2. Frontend Architecture

- **Path**: `frontend/`
- **Framework**: React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide icons, Zustand.

### Directory Structure
```
frontend/src/
├── components/
│   ├── Sidebar.tsx         # Navigation sidebar with active route highlighting
│   ├── TopBar.tsx          # Organization/project context & notifications bell
│   └── ui/                 # 26 Canonical Shared UI Primitives:
│       ├── Button.tsx, IconButton.tsx
│       ├── Input.tsx, Textarea.tsx, Select.tsx, Checkbox.tsx, Switch.tsx, FormField.tsx
│       ├── Badge.tsx, Alert.tsx, Toast.tsx
│       ├── Modal.tsx, Drawer.tsx, Tabs.tsx, Card.tsx
│       ├── Table.tsx, Pagination.tsx, DropdownMenu.tsx, Tooltip.tsx
│       ├── Skeleton.tsx, Spinner.tsx, EmptyState.tsx, ErrorState.tsx
│       └── PageHeader.tsx, Breadcrumbs.tsx, ConfirmDialog.tsx
├── layouts/
│   └── AppShell.tsx        # Shell layout with route protection & PublicLayout
├── pages/
│   ├── Landing.tsx, Login.tsx, Register.tsx, Documentation.tsx
│   ├── Dashboard.tsx, ScansList.tsx, Reports.tsx, Analytics.tsx
│   ├── Notifications.tsx, Settings.tsx, FindingsList.tsx, Integrations.tsx, Team.tsx
│   └── projects/
│       ├── ProjectsList.tsx, CreateProject.tsx, ProjectDetail.tsx
│       ├── ConnectRepo.tsx, ScanConfig.tsx, ScanProgress.tsx
│       └── ScanResultsWorkspace.tsx
├── services/
│   ├── api.ts              # Central Axios client with token injection & error unwrapping
│   ├── authService.ts      # Login, registration, token refresh, logout
│   ├── projectService.ts   # Project CRUD
│   ├── scanService.ts      # Scan creation, listing, status, cancellation
│   ├── uploadService.ts    # File upload handling
│   └── resultService.ts    # Findings/scan results retrieval
├── store.ts                # Minimal global Zustand stores (Auth, Notifications, Theme)
└── types.ts                # TypeScript domain models and API envelopes
```

### Route Map (Phase 0 Canonical)
- **Public**: `/`, `/login`, `/register`, `/documentation`
- **Authenticated Application**:
  - `/dashboard`
  - `/projects`, `/projects/create`, `/projects/:projectId`
  - `/projects/:projectId/repository`
  - `/projects/:projectId/scan-config`
  - `/projects/:projectId/scan-progress/:scanId`
  - `/projects/:projectId/scans`
  - `/projects/:projectId/findings`
  - `/projects/:projectId/reports`
  - `/projects/:projectId/settings`
  - `/scans`, `/findings`, `/reports`, `/analytics`, `/integrations`, `/team`, `/notifications`, `/settings`

---

## 3. Backend Architecture

- **Path**: `backend/`
- **Framework**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Alembic, Celery, Redis.

### Layered Separation
```
API ROUTER  ──>  SERVICE LAYER  ──>  REPOSITORY LAYER  ──>  DATABASE (PostgreSQL)
     │                 │
     └── Auth & RBAC   └── STORAGE ABSTRACTION (LocalStorage / S3)
```

1. **API Routers (`backend/app/routers/`)**:
   - HTTP orchestration only: request schema validation, dependency injection, and status codes.
   - `auth_router.py`, `project_router.py`, `upload_router.py`, `scan_router.py`, `result_router.py`, `report_router.py`, `notification_router.py`, `analytics_router.py`, `health_router.py`, `websocket_router.py`.

2. **Service Layer (`backend/app/services/`)**:
   - Pure domain business logic, access verification, audit logging dispatch.
   - `auth_service.py`, `project_service.py`, `upload_service.py`, `scan_service.py`, `audit_service.py`, etc.

3. **Repository Layer (`backend/app/repositories/`)**:
   - Explicit, isolated database queries using SQLAlchemy 2.0 async select/update/delete.
   - `user_repository.py`, `project_repository.py`, `upload_repository.py`, `scan_repository.py`, `result_repository.py`, `audit_repository.py`, etc.

4. **Storage Abstraction (`backend/app/storage/`)**:
   - Abstract `StorageBackend` base class defining `store`, `retrieve`, `delete`, and `get_url`.
   - `LocalStorage` implementation enforces containment within configured storage root, generates collision-safe UUID paths, and blocks path traversal.
   - Unified `StorageService` provides high-level domain operations.

5. **Security & Utilities (`backend/app/core/`, `backend/app/utils/`)**:
   - `permissions.py`: JWT-based identity verification (`get_current_active_user`, `require_admin`, `require_project_access`).
   - `security.py`: Password hashing (bcrypt) and JWT encode/decode.
   - `zip_utils.py`: Hardened archive extraction checking Zip-Slip, path traversal, symlink escapes, max archive size, and max entry count.

---

## 4. Database & Alembic

- **Authoritative Schema**: Alembic migrations under `backend/alembic/versions/`.
- Startup table creation via `Base.metadata.create_all()` is **disabled**.
- Baseline Migration `0001_initial_baseline.py` covers Phase 1 models.
- Migration `0002_phase2_identity_org_rbac.py` expands the schema to 24 tables, adding:
  13. `organizations` (tenants with UUID PK, slug uniqueness, active state)
  14. `organization_members` (user-org memberships with status lifecycle & composite uniqueness)
  15. `organization_invitations` (token-hashed expiring invitations)
  16. `roles` (5 system roles: owner, admin, security_analyst, developer, viewer)
  17. `permissions` (36 granular capabilities across 10 categories)
  18. `role_permissions` (composite mapped RBAC assignments)
  19. `sessions` (server-tracked revocable sessions with refresh token hashes)
  20. `verification_tokens` (one-time hashed email verification and password reset tokens)
  21. `api_keys` (display prefix + SHA-256 hashed keys)
  22. `repository_branches` (composite unique branch records per repository)
  23. `repository_commits` (immutable commit records per repository)
  - Upgrades `projects` with `organization_id` foreign key and composite uniqueness.
  - Upgrades `audit_logs` with `organization_id` foreign key and indexing.

---

## 5. Phase 2 Multi-Tenant RBAC & Identity Architecture

### 5.1 Relational Ownership Hierarchy
Every protected operation strictly adheres to the frozen Phase 0 hierarchy:
```
Organization
    ↓
Membership (Status: active, suspended, removed)
    ↓
Role (owner, admin, security_analyst, developer, viewer)
    ↓
Permissions (e.g., project.read, team.invite, scan.create)
```

### 5.2 Mandatory Tenant-Safe Authorization Pattern
Endpoints never resolve resources purely by UUID. Client-provided UUIDs are only identifiers and never proof of access.
The central dependency `resolve_organization_context` validates:
1. Valid JWT token with session ID.
2. Server-side session is active and not revoked in `sessions` table.
3. Target organization ID resolved from URL path (`/organizations/{organization_id}/...`) or header (`X-Organization-ID`).
4. Active membership in `organization_members` with status `active`.
5. User's role grants required granular permission in `role_permissions`.
6. Resource queries join `organization_id` at the database boundary to eliminate IDOR and BOLA attacks.

### 5.3 Baseline Role-Permission Matrix
- **OWNER**: Full administrative control across all resources and team management. Sole owner cannot be demoted or removed.
- **ADMIN**: Organization administration, team invitations, member management, project & scan management (cannot delete organization or demote sole owner).
- **SECURITY_ANALYST**: Read projects/repos/scans, create/cancel scans, finding triage, risk acceptance, remediation management, and audit log inspection.
- **DEVELOPER**: Read permitted projects/repos, launch permitted scans, inspect findings, and create remediation requests. Cannot manage team or view audit logs.
- **VIEWER**: Strict read-only visibility across authorized projects, repositories, scans, and reports. All mutation endpoints return 403 Forbidden.

### 5.4 Revocable Sessions & Token Security
- **Access Tokens**: Short-lived JWTs (60 min) containing `sub`, `email`, and `sid` (session ID).
- **Refresh Sessions**: Tracked in `sessions` table. Refresh secrets are SHA-256 hashed before storage; plain secrets are never persisted.
- **Refresh Rotation**: Every token refresh invalidates the current refresh hash and issues a new pair. Replay of old refresh tokens triggers revocation.
- **Server-Side Logout**: `/auth/logout` sets `revoked_at = now()` in the `sessions` table. Client requests with revoked tokens immediately fail with 401.
- **Password Reset**: Invalidates all existing active user sessions in the database upon successful completion.

### 5.5 Secret Protection & Audit Immutability
- **API Keys**: Issued with format `xai_<prefix>_<secret>`. The database only stores `key_prefix` and SHA-256 hash. Plain secrets are returned once at creation.
- **Verification & Reset Tokens**: Cryptographically random 32-byte tokens, hashed before storage in `verification_tokens`. One-time use with expiration.
- **Audit Logs**: Durable, append-only security logs. Passwords, raw tokens, API secrets, and authorization headers are strictly excluded from audit metadata.

---

## 6. Celery & Redis Infrastructure

- Celery configured in `backend/app/workers/celery_app.py` with Redis broker (`/1`) and result backend (`/2`).
- Task routing divides queues: `default_queue` and `ai_queue`.
- Dedicated `ping_infrastructure` task in `backend/app/workers/health_task.py` provides an isolated infrastructure readiness test without simulating fake scans.

---

## 7. Security Guarantees in Phase 2

1. **Admin Self-Registration Blocked**:
   Public user registration creates an isolated organization where the user is Owner of their own tenant, but cannot self-assign Admin/Owner roles to other organizations.
2. **Tenant Isolation & Anti-IDOR**:
   Knowing another organization's UUID, project UUID, or repository UUID returns 403/404. All database queries enforce organizational boundaries.
3. **Owner Invariant Protection**:
   The final owner of an organization cannot be demoted or removed. Attempting to do so raises a 422 Validation Error.
4. **Path Traversal & Zip-Slip Protection**:
   Preserved from Phase 1.
5. **Controlled Error Responses**:
   Unhandled internal exceptions are converted to safe HTTP 500 envelopes by `register_exception_handlers` without leaking Python tracebacks, SQL queries, or filesystem paths.

---

## 8. Explicitly Deferred Phase 3–8 Features

The following features belong strictly to future phases and are intentionally NOT implemented in Phase 2:
- **Phase 3**: Real Git clone/webhook sync (GitHub/GitLab apps), AST/source snapshot preprocessing.
- **Phase 4**: Joern scanning engine, CPG/CFG/PDG graph generation, data-flow & taint analysis execution.
- **Phase 5**: GNN & CodeBERT model inference pipelines, real vulnerability prediction correlation.
- **Phase 6**: XAI explanations (Captum/integrated gradients), LLM remediation generation, automated patch validation.
- **Phase 7**: Automated PDF/HTML report exports, external CI/CD & PR scan integrations.
- **Phase 8**: Production hardening, HA scaling, distributed worker clusters.
