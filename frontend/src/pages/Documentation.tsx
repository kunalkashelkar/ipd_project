import React, { useState } from 'react';
import {
  BookOpen,
  Shield,
  Cpu,
  Network,
  Layers,
  GitBranch,
  FileText,
  Users,
  CheckCircle2,
  AlertTriangle,
  Info,
  ChevronRight,
  Terminal,
  Server,
  Key,
  Bell,
  BarChart3,
  Search,
  Lock,
  Workflow,
  Sparkles,
  FileCode,
  Activity,
  HardDrive,
  Database,
  ExternalLink,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, Badge, Button } from '../components/ui';

interface DocSection {
  id: string;
  category: string;
  title: string;
  icon: React.ReactNode;
  badge: 'Available' | 'Configuration required' | 'Environment-dependent';
  badgeVariant: 'default' | 'outline' | 'secondary';
  overview: string;
  subsections: {
    title: string;
    content: string;
    details?: string[];
    codeBlock?: string;
  }[];
  apiEndpoints?: string[];
  keyInvariants?: string[];
}

const DOCUMENTATION_SECTIONS: DocSection[] = [
  {
    id: 'platform-overview',
    category: 'Architecture',
    title: 'Platform Overview & Architecture',
    icon: <Layers className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'VulnScan delivers deep static analysis, program dependence graph (PDG) construction, taint tracking, and evidence-aware AI vulnerability detection with automated remediation validation.',
    subsections: [
      {
        title: 'System Architecture & Runtime Stack',
        content:
          'The platform is built as a cloud-native, multi-tenant system structured into decoupled services and asynchronous workers:',
        details: [
          'Web API Layer: FastAPI running with async greenlet runtime, enforcing strict tenant isolation, RBAC permissions, and standardized envelope responses.',
          'Database Layer: PostgreSQL 15+ managing authoritative schema entities with transactional DDL migrations via Alembic.',
          'Distributed Task Queue: Celery 5.4+ with Redis 7+ broker orchestrating multi-stage analysis, report rendering, and git synchronization.',
          'Object Storage: MinIO/S3-compatible storage isolating immutable source archives, canonical graphs, patch diffs, and report artifacts.',
          'Frontend Interface: React 18, Vite, and Tailwind CSS with real-time SSE progress, Cytoscape graph visualization, and Monaco code inspection.',
        ],
      },
      {
        title: 'Multi-Tenant Isolation Model',
        content:
          'All resources (Projects, Repositories, Snapshots, Scans, Findings, Reports, Notifications) are strictly scoped to an Organization. Access requires verified OrganizationMember association; cross-tenant queries are blocked at both the repository and query boundary.',
      },
      {
        title: 'Data Flow & Trust Boundaries',
        content:
          'Untrusted source code is ingested into isolated snapshots, validated for directory traversal (ZipSlip protection), and analyzed in sandboxed worker execution boundaries. Raw code never leaves local tenant storage.',
      },
    ],
    keyInvariants: [
      'Strict organization-level tenant partitioning on all domain tables.',
      'Immutable source snapshots ensuring deterministic scan reproducibility.',
      'Uniform machine-readable error contracts (error code, message, request ID).',
    ],
    apiEndpoints: ['GET /api/v1/health', 'GET /api/v1/health/ready', 'GET /api/v1/organizations'],
  },
  {
    id: 'security-analysis',
    category: 'Analysis',
    title: 'Security Analysis & Graph Engine',
    icon: <Network className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Multi-tiered static and semantic vulnerability analysis combining Abstract Syntax Trees (AST), Control Flow Graphs (CFG), Program Dependence Graphs (PDG), and interprocedural taint propagation.',
    subsections: [
      {
        title: 'Source Ingestion & Immutable Snapshots',
        content:
          'Source code is ingested via Git branch checkout or compressed ZIP uploads. Ingestion generates a cryptographic SHA-256 content hash, extracting normalized functions while rejecting path traversal (ZipSlip), symbolic link attacks, and excessive archive sizes (zip bomb defense).',
      },
      {
        title: 'Deterministic Graph Generation',
        content:
          'Parsers generate AST, CFG, and Call Graph representations. Where Joern/native analyzers are present, full interprocedural PDGs are produced; fallback analyzers maintain synthetic graph continuity for consistent UI rendering.',
      },
      {
        title: 'Taint Analysis Pipeline',
        content:
          'Tracks dataflow paths from untrusted user inputs (sources) through sanitizers to sensitive execution sinks (e.g., SQL queries, DOM rendering, OS commands). Taint state is classified into UNTAINTED, POTENTIALLY_TAINTED, and TAINTED.',
      },
      {
        title: 'AI-Assisted Detection & Inference',
        content:
          'Extracts function-level slices and feeds them to the configured AI Provider boundary. In production, local HuggingFace/Torch weights analyze code context; in local development, deterministic rule-backed providers supply reproducible finding hypotheses.',
      },
    ],
    keyInvariants: [
      'Zero execution of untrusted user source code during analysis.',
      'Separation of static proof evidence and statistical AI predictions.',
      'Deterministic deduplication of repeated occurrences across subsequent scans.',
    ],
    apiEndpoints: [
      'POST /api/v1/projects/{id}/snapshots',
      'POST /api/v1/scans',
      'GET /api/v1/scans/{id}/status',
    ],
  },
  {
    id: 'findings-lifecycle',
    category: 'Findings',
    title: 'Finding Lifecycle & Fingerprinting',
    icon: <Shield className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Authoritative vulnerability tracking from detection through verification, triaging, assignment, and historical deduplication.',
    subsections: [
      {
        title: 'Authoritative Fingerprinting',
        content:
          'Findings are deduplicated using a canonical SHA-256 fingerprint derived from normalized function signature, CWE category, vulnerability type, and relative file path. Line-shift invariant fingerprinting ensures findings survive refactorings.',
      },
      {
        title: 'Lifecycle State Machine',
        content:
          'Findings transition through formal authoritative states: OPEN → TRIAGED → REMEDIATING → FIXED → VERIFIED. Supported governance states include FALSE_POSITIVE, SUPPRESSED, and RISK_ACCEPTED.',
        details: [
          'OPEN: Detected and active in the codebase requiring attention.',
          'FIXED: A subsequent scan verifies the vulnerability occurrence is no longer present in source.',
          'VERIFIED: Remediation validation suite successfully proved the patch neutralizes the vulnerability.',
          'REOPENED: An issue previously marked FIXED or SUPPRESSED has resurfaced in a newer commit.',
        ],
      },
      {
        title: 'Collaboration & Mentions',
        content:
          'Teams can assign findings to organization members, post threaded triage comments, and @mention teammates. Mentioning emits real-time in-app notifications.',
      },
    ],
    keyInvariants: [
      'Deterministic finding fingerprints immune to cosmetic line-number shifts.',
      'Authoritative lifecycle transitions recorded with audit logs and timestamps.',
    ],
    apiEndpoints: [
      'GET /api/v1/findings',
      'GET /api/v1/findings/{id}',
      'PATCH /api/v1/findings/{id}/status',
      'POST /api/v1/findings/{id}/comments',
    ],
  },
  {
    id: 'explainability-remediation',
    category: 'Remediation',
    title: 'Explainability & Remediation Engine',
    icon: <Cpu className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Contextualized vulnerability explanations, automated patch generation, and isolated containerized patch validation.',
    subsections: [
      {
        title: 'Evidence-Aware Explanations (XAI)',
        content:
          'Synthesizes taint paths, AST node tokens, and vulnerable code context into natural language explanations. Attribution methods pinpoint exact input sources and unsanitized sink expressions.',
      },
      {
        title: 'Automated Remediation Generation',
        content:
          'Proposes unified diff patches targeting vulnerable functions with sanitized replacements (e.g. parameterized queries, safe HTML encoders).',
      },
      {
        title: 'Multi-Stage Patch Validation',
        content:
          'Candidate patches are tested in an isolated workspace: applying the diff cleanly, checking syntax trees, running unit tests, and executing a verification scan to prove vulnerability mitigation without regressions.',
      },
    ],
    keyInvariants: [
      'Remediation patches must pass syntax checking before being marked proposed.',
      'Re-occurrence of a previously verified finding automatically reopens the finding.',
    ],
    apiEndpoints: [
      'POST /api/v1/findings/{id}/explain',
      'POST /api/v1/findings/{id}/remediations',
      'POST /api/v1/remediations/{id}/validate',
    ],
  },
  {
    id: 'analytics-health',
    category: 'Analytics',
    title: 'Analytics & Security Health Score',
    icon: <BarChart3 className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Versioned Security Health Score (v1.0.0), historical trend analytics, CWE distribution, remediation velocity, and authoritative scan comparisons.',
    subsections: [
      {
        title: 'Security Health Score (v1.0.0)',
        content:
          'The platform calculates a deterministic posture score from 0.0 to 100.0 based on authoritative finding records:',
        details: [
          'Base Score: 100.0 pts',
          'Critical Penalty: -15.0 pts per active critical vulnerability',
          'High Penalty: -8.0 pts per active high vulnerability',
          'Medium Penalty: -3.0 pts per active medium vulnerability',
          'Low Penalty: -1.0 pts per active low vulnerability',
          'Remediation Bonus: + 10.0 * (Resolved Findings / Total Findings)',
          'Rating Mapping: A (90-100), B (80-89.9), C (70-79.9), D (60-69.9), F (<60)',
        ],
      },
      {
        title: 'Truthful Empty Workspace Semantics',
        content:
          'If no completed scan exists for an organization or project, the health score returns NO_DATA (score: null, rating: null). 100/A is awarded only when an assessment actually completes with zero active vulnerabilities.',
      },
      {
        title: 'Authoritative Scan Comparison',
        content:
          'Compares two completed scans within the same project using finding fingerprints. Outputs existing findings, new findings (introduced), fixed findings (resolved, displayed as a positive integer count), and reopened findings.',
      },
    ],
    keyInvariants: [
      'Zero completed scans always renders NO_DATA rather than default 100/A.',
      'Comparison strictly rejects cross-project, cross-tenant, or non-completed scans.',
      'Fixed findings represent positive resolution count.',
    ],
    apiEndpoints: [
      'GET /api/v1/analytics',
      'GET /api/v1/analytics/dashboard',
      'POST /api/v1/analytics/compare',
    ],
  },
  {
    id: 'reports',
    category: 'Reports',
    title: 'Compliance & Security Reports',
    icon: <FileText className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Asynchronous report generation across a complete 12-combination matrix with durable object storage and SHA-256 verification.',
    subsections: [
      {
        title: 'Report Type & Format Matrix',
        content:
          'Supports all 12 combinations: {Developer, Security, Executive} × {PDF, HTML, JSON, CSV}:',
        details: [
          'Developer Report: Focuses on file paths, code line numbers, taint evidence, and remediation diffs.',
          'Security Report: Full technical audit with CVSS scores, CWE taxonomy, risk metrics, and occurrence logs.',
          'Executive Report: High-level posture summaries, rating cards, vulnerability distributions, and MTTR trends.',
          'PDF: Professional multi-page layout rendered using ReportLab with tables and status badges.',
          'HTML: Standalone responsive web page with inline styling for offline audit sharing.',
          'JSON: Structured machine-readable schema for SIEM/data-pipeline ingestion.',
          'CSV: Sanitized tabular format with formula injection protection (=, +, -, @ escaped).',
        ],
      },
      {
        title: 'Asynchronous Workflow & Storage',
        content:
          'Reports are requested via POST /api/v1/reports returning HTTP 202 Accepted. Celery workers collect authoritative scan records, render artifact bytes, calculate SHA-256 checksums, and store files at tenant-partitioned object storage keys.',
      },
    ],
    keyInvariants: [
      'Artifact checksums and byte counts stored in report_files database table.',
      'Formula injection mitigation on all generated CSV exports.',
      'Downloads securely streamed via authenticated endpoints verifying tenant ownership.',
    ],
    apiEndpoints: [
      'GET /api/v1/reports',
      'POST /api/v1/reports',
      'GET /api/v1/reports/{id}',
      'GET /api/v1/reports/{id}/download',
    ],
  },
  {
    id: 'integrations-cicd',
    category: 'Integrations',
    title: 'Integrations, GitHub App & CI/CD',
    icon: <GitBranch className="w-4 h-4 text-primary" />,
    badge: 'Configuration required',
    badgeVariant: 'secondary',
    overview:
      'GitHub pull request analysis, HMAC-verified webhooks, configurable Security Gates, lightweight Python CLI, and native GitHub Action.',
    subsections: [
      {
        title: 'Capability Status & Verification Matrix',
        content:
          'To maintain operational transparency, integration capabilities are categorized by verification and configuration state:',
        details: [
          'GitHub Webhook Verification: Available (HMAC SHA-256 signature verification & delivery deduplication implemented and verified locally).',
          'GitHub App: Configuration required (Requires registered GitHub App, private key, and workspace installation; truthfully reported as unconfigured when credentials are absent).',
          'GitHub Pull Request Security Analysis: Configuration required (Automated analysis pipeline and baseline diffing implemented locally; live Check Run creation requires external GitHub App configuration).',
          'CI/CD API: Available (Scan creation, status polling, and security gate evaluation endpoints active).',
          'CLI: Available (Canonical security_cli.py with exit codes 0 for pass, 1 for gate failure, 2 for execution error).',
          'GitHub Action: Available (Reusable workflow in .github/workflows/security-gate.yml ready for pipeline integration).',
        ],
      },
      {
        title: 'GitHub Webhook Ingestion & Security',
        content:
          'Inbound webhooks at /api/v1/integrations/github/webhook enforce HMAC SHA-256 signatures via X-Hub-Signature-256 and replay protection via X-GitHub-Delivery idempotency tracking.',
      },
      {
        title: 'Project Security Gates',
        content:
          'Configurable per-project quality gates evaluate pull request scans against policy rules: Block New Critical, Block New High, Block Hardcoded Secrets, and Maximum CVSS Threshold. Evaluates only NEW vulnerabilities introduced by the PR.',
      },
      {
        title: 'Canonical Security CLI Contract',
        content:
          'Standalone CLI requiring only Python standard library. Interacts with CI endpoints with standardized exit codes:',
        details: [
          'Exit Code 0: Scan completed and Security Gate PASSED.',
          'Exit Code 1: Security Gate FAILED (policy violation detected).',
          'Exit Code 2: Execution error (timeout, connection failure, bad arguments).',
        ],
        codeBlock:
          '# Canonical CLI Usage\npython -m cli.security_cli scan --project prj_5tfz928n7csu --wait --timeout 300\npython -m cli.security_cli status scan_9km4q72vx\npython -m cli.security_cli gate scan_9km4q72vx',
      },
      {
        title: 'GitHub Action Integration',
        content:
          'The platform includes a reusable GitHub Action (.github/actions/security-scan/action.yml) ready to embed into PR workflows.',
      },
    ],
    keyInvariants: [
      'Security gates evaluate authoritative NEW findings against the baseline.',
      'Delivery ID deduplication prevents duplicate webhook executions.',
      'GitHub App status truthfully reported as Not configured when external credentials are absent.',
    ],
    apiEndpoints: [
      'POST /api/v1/integrations/github/webhook',
      'GET /api/v1/integrations/github/status',
      'GET /api/v1/projects/{id}/gate-policy',
      'PUT /api/v1/projects/{id}/gate-policy',
      'POST /api/v1/ci/scans',
      'GET /api/v1/ci/scans/{id}/gate',
    ],
  },
  {
    id: 'notifications-events',
    category: 'Operations',
    title: 'Notification System & Domain Events',
    icon: <Bell className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Real-time in-app notification center tracking 7 authoritative domain events with idempotency deduplication.',
    subsections: [
      {
        title: 'Canonical Domain Event Triggers',
        content: 'Notifications are emitted from authoritative service execution points:',
        details: [
          'scan_completed: Emitted to all project members when an analysis pipeline finishes.',
          'critical_finding: Emitted when an authoritative Critical severity finding is identified.',
          'fix_ready: Emitted when an AI remediation proposal is generated and ready for review.',
          'fix_validated: Emitted following automated patch validation (pass or fail).',
          'finding_reopened: Emitted when a previously resolved/suppressed vulnerability reoccurs.',
          'repository_disconnected: Emitted when a repository connection is unlinked.',
          'user_mentioned: Emitted when a user is tagged in a finding comment.',
        ],
      },
      {
        title: 'Deduplication & Delivery Invariants',
        content:
          'Each event uses an event_key composite string (e.g. critical_finding:{finding_id}:{user_id}) to prevent spamming notifications on repeated scans.',
      },
    ],
    keyInvariants: [
      'Zero synthetic notification creation — all records stem from real domain state transitions.',
      'Deduplicated via unique composite event_key per recipient.',
    ],
    apiEndpoints: [
      'GET /api/v1/notifications',
      'GET /api/v1/notifications/unread-count',
      'PATCH /api/v1/notifications/{id}/read',
      'POST /api/v1/notifications/mark-all-read',
    ],
  },
  {
    id: 'team-rbac',
    category: 'Security',
    title: 'Team, Roles & Access Control',
    icon: <Users className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Role-based access control (RBAC) across five tiered roles, secure invitation workflows, and comprehensive security audit logging.',
    subsections: [
      {
        title: 'Tiered RBAC Roles',
        content: 'Permissions are enforced at the API dependency layer across five distinct roles:',
        details: [
          'Owner: Full organization ownership, membership management, billing, and project deletion.',
          'Admin: User management, project creation, security gate policies, and repository management.',
          'Security Engineer: Scan execution, finding triage, risk acceptance, remediation validation, and report export.',
          'Developer: Read project scans, view assigned findings, request remediation proposals, and comment.',
          'Viewer: Read-only access to completed scans and executive metrics.',
        ],
      },
      {
        title: 'Audit Logging System',
        content:
          'Every security-relevant action (login, role change, finding status change, remediation validation, gate update, report download) writes an immutable AuditLog record containing actor, action, IP address, and resource metadata.',
      },
    ],
    keyInvariants: [
      'Owners cannot be downgraded if they are the sole owner of an organization.',
      'Audit logs are append-only with no modification or deletion endpoints.',
    ],
    apiEndpoints: [
      'GET /api/v1/organizations/{id}/team/members',
      'GET /api/v1/organizations/{id}/team/roles',
      'POST /api/v1/organizations/{id}/team/invitations',
      'GET /api/v1/audit-logs',
    ],
  },
  {
    id: 'operations-deployment',
    category: 'Operations',
    title: 'Operations, Monitoring & Runbooks',
    icon: <Server className="w-4 h-4 text-primary" />,
    badge: 'Available',
    badgeVariant: 'default',
    overview:
      'Deployment architectures, environment configurations, container health checks, database maintenance, and operational runbooks.',
    subsections: [
      {
        title: 'Docker Compose Stack',
        content:
          'Standard deployment consists of 6 networked containers: backend (FastAPI), celery_worker, postgres (PostgreSQL 15), redis (Redis 7), minio (MinIO S3), and frontend (Vite/Nginx).',
      },
      {
        title: 'Database Migrations & Head Verification',
        content:
          'Schema updates are tracked in backend/alembic/versions. Upgrades and downgrades are strictly reversible:',
        codeBlock:
          '# Alembic Reversibility Check\nalembic current\nalembic downgrade -1\nalembic upgrade head',
      },
      {
        title: 'Health Diagnostics',
        content:
          'GET /api/v1/health returns application liveness; GET /api/v1/health/ready checks PostgreSQL database and Redis connectivity before routing traffic.',
      },
    ],
    keyInvariants: [
      'Liveness and readiness probes verify downstream database and cache health.',
      'Secrets stored strictly in environment variables or container secret vaults.',
    ],
    apiEndpoints: ['GET /api/v1/health', 'GET /api/v1/health/ready'],
  },
];

export default function Documentation() {
  const [selectedSectionId, setSelectedSectionId] = useState<string>('platform-overview');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const selectedSection =
    DOCUMENTATION_SECTIONS.find((s) => s.id === selectedSectionId) || DOCUMENTATION_SECTIONS[0];

  const filteredSections = DOCUMENTATION_SECTIONS.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.title.toLowerCase().includes(q) ||
      s.overview.toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Page Header */}
      <div className="border-b border-border/60 pb-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Shield className="w-5 h-5 text-primary" />
              <h1 className="text-2xl font-bold font-display tracking-tight text-foreground">
                Platform Documentation
              </h1>
            </div>
            <p className="text-xs text-muted-foreground">
              Technical reference, architecture invariants, security contracts, and operational guides for the VulnScan platform.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs font-mono bg-primary/5 text-primary border-primary/20">
              System Architecture v1.0
            </Badge>
          </div>
        </div>
      </div>

      {/* Main Layout: Sidebar Navigation & Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Sidebar Navigation */}
        <div className="lg:col-span-4 space-y-4">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search documentation..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-8 pl-8 pr-3 text-xs rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="space-y-1">
            {filteredSections.map((sec) => {
              const isSelected = sec.id === selectedSection.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setSelectedSectionId(sec.id)}
                  className={`w-full text-left p-2.5 rounded-lg text-xs transition-all flex items-center justify-between group ${
                    isSelected
                      ? 'bg-primary/10 text-primary font-semibold border border-primary/30'
                      : 'text-muted-foreground hover:bg-muted/30 hover:text-foreground border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className={isSelected ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}>
                      {sec.icon}
                    </span>
                    <span className="truncate">{sec.title}</span>
                  </div>
                  <ChevronRight
                    className={`w-3.5 h-3.5 shrink-0 transition-transform ${
                      isSelected ? 'transform rotate-90 text-primary' : 'text-muted-foreground/50'
                    }`}
                  />
                </button>
              );
            })}
          </div>

          <Card className="border-border/80 bg-muted/10 p-3.5 text-xs">
            <h4 className="font-semibold text-foreground flex items-center gap-1.5 mb-1.5">
              <Terminal className="w-3.5 h-3.5 text-primary" /> CI/CD Quick Start
            </h4>
            <p className="text-[11px] text-muted-foreground mb-2">
              Automate pull request scans directly from terminal or CI pipelines:
            </p>
            <pre className="p-2 bg-background rounded border border-border/40 font-mono text-[10px] text-foreground/90 overflow-x-auto">
              python -m cli.security_cli scan --project prj_... --wait
            </pre>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="lg:col-span-8 space-y-6">
          <Card className="border-border/80">
            <CardHeader className="border-b border-border/40 pb-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                    {selectedSection.icon}
                  </div>
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                      {selectedSection.category}
                    </span>
                    <CardTitle className="text-lg font-bold text-foreground">
                      {selectedSection.title}
                    </CardTitle>
                  </div>
                </div>
                <Badge
                  variant={selectedSection.badgeVariant}
                  className="text-[10px] font-medium bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                >
                  {selectedSection.badge}
                </Badge>
              </div>
              <CardDescription className="text-xs text-muted-foreground pt-2">
                {selectedSection.overview}
              </CardDescription>
            </CardHeader>

            <CardContent className="p-6 space-y-6">
              {/* Detailed Subsections */}
              <div className="space-y-6">
                {selectedSection.subsections.map((sub, idx) => (
                  <div key={idx} className="space-y-2">
                    <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                      {sub.title}
                    </h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {sub.content}
                    </p>

                    {sub.details && (
                      <ul className="space-y-1.5 pl-4 pt-1">
                        {sub.details.map((d, dIdx) => (
                          <li key={dIdx} className="text-xs text-muted-foreground list-disc marker:text-primary/70">
                            {d}
                          </li>
                        ))}
                      </ul>
                    )}

                    {sub.codeBlock && (
                      <pre className="mt-2 p-3 bg-muted/40 rounded-lg border border-border/60 font-mono text-[11px] text-foreground overflow-x-auto">
                        {sub.codeBlock}
                      </pre>
                    )}
                  </div>
                ))}
              </div>

              {/* Key System Invariants */}
              {selectedSection.keyInvariants && selectedSection.keyInvariants.length > 0 && (
                <div className="pt-4 border-t border-border/40">
                  <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> System Invariants & Guarantees
                  </h4>
                  <div className="space-y-1.5">
                    {selectedSection.keyInvariants.map((inv, iIdx) => (
                      <div
                        key={iIdx}
                        className="p-2 bg-muted/20 rounded border border-border/40 text-xs text-foreground flex items-start gap-2"
                      >
                        <span className="text-emerald-500 font-bold">•</span>
                        <span>{inv}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Associated API Endpoints */}
              {selectedSection.apiEndpoints && selectedSection.apiEndpoints.length > 0 && (
                <div className="pt-4 border-t border-border/40">
                  <h4 className="text-xs font-semibold text-foreground uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <ExternalLink className="w-3.5 h-3.5 text-primary" /> Associated API Endpoints
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {selectedSection.apiEndpoints.map((ep, eIdx) => (
                      <div
                        key={eIdx}
                        className="p-2 bg-background rounded border border-border/50 font-mono text-[11px] text-foreground/90 truncate"
                      >
                        {ep}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
