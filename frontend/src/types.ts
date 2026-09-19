// ============================================================
// Shared TypeScript Types — Matching Backend Schemas
// ============================================================

// ── Auth ─────────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  role: 'admin' | 'researcher' | 'developer' | 'viewer';
  is_active?: boolean;
  created_at?: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: User;
  organization?: Organization;
  active_organization?: Organization;
  organizations?: Organization[];
  tokens: TokenPair;
}

// ── Organizations & Multi-Tenancy ─────────────────────────────

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  is_active: boolean;
  current_user_role?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  user_name: string;
  user_email: string;
  role: 'owner' | 'admin' | 'security_analyst' | 'developer' | 'viewer';
  status: 'active' | 'suspended' | 'removed';
  joined_at: string;
}

export interface OrganizationInvitation {
  id: string;
  organization_id: string;
  invited_email: string;
  role_name: string;
  status: 'pending' | 'accepted' | 'cancelled' | 'expired';
  invitation_token?: string;
  expires_at: string;
  created_at: string;
}

export interface Permission {
  id: string;
  key: string;
  description: string | null;
  category: string;
}

export interface RoleWithPermissions {
  id: string;
  name: string;
  description: string | null;
  permissions: Permission[];
}

export interface ApiKeyMetadata {
  id: string;
  name: string;
  key_prefix: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
  created_at: string;
}

// ── Projects ─────────────────────────────────────────────────

export interface Project {
  id: string;
  public_id: string;
  name: string;
  description: string | null;
  language: string | null;
  default_branch: string | null;
  owner_id: string;
  organization_id?: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  // UI-only computed fields (optional)
  visibility?: 'private' | 'public' | 'internal';
  repository_url?: string;
  last_scan_at?: string;
  risk_score?: number;
  status?: 'active' | 'archived';
}

// ── Uploads ──────────────────────────────────────────────────

export interface Upload {
  id: string;
  project_id: string;
  user_id: string;
  original_filename: string;
  stored_filename: string;
  stored_path: string;
  file_size: number;
  file_extension: string;
  status: string;
  created_at: string;
}

// ── Scans ────────────────────────────────────────────────────

export type ScanStatus =
  | 'pending'
  | 'queued'
  | 'preparing'
  | 'checkout'
  | 'preprocessing'
  | 'static_analysis'
  | 'graph_processing'
  | 'ai_analysis'
  | 'post_processing'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'timed_out'
  | 'retrying'
  | 'running';

export interface Scan {
  id: string;
  public_id: string;
  project_id: string;
  project_name?: string | null;
  project_public_id?: string | null;
  organization_id?: string | null;
  upload_id: string | null;
  repository_id: string | null;
  source_snapshot_id?: string | null;
  source_snapshot_version?: string | null;
  source_snapshot_public_id?: string | null;
  user_id?: string;
  status: ScanStatus;
  progress: number;
  current_stage: string | null;
  stage_attempt?: number;
  retry_count?: number;
  timeout_seconds?: number;
  worker_id?: string | null;
  heartbeat_at?: string | null;
  failure_code?: string | null;
  failure_reason?: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at?: string | null;
  config?: Record<string, any> | null;
  ai_model_version?: string | null;
  created_at: string;
}

export interface ScanStatusInfo {
  id: string;
  status: ScanStatus;
  progress: number;
  current_stage: string | null;
  failure_code?: string | null;
  failure_reason?: string | null;
  cancelled_at?: string | null;
  error_message?: string | null;
}

export interface ScanStageRun {
  id: string;
  scan_id: string;
  stage: string;
  attempt: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  worker_id?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  stage_metadata?: Record<string, any> | null;
  created_at: string;
}

export interface AnalysisArtifact {
  id: string;
  scan_id: string;
  source_snapshot_id: string;
  artifact_type: string;
  schema_version: string;
  artifact_uri: string;
  content_hash: string;
  size_bytes: number;
  status: string;
  tool_name?: string | null;
  tool_version?: string | null;
  node_count: number;
  edge_count: number;
  artifact_metadata?: Record<string, any> | null;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
}

export interface TaintPathEvidence {
  path_id: string;
  source_id: string;
  sink_id: string;
  length: number;
  nodes: string[];
  risk_score: number;
  source_file?: string | null;
  source_line?: number | null;
  sink_file?: string | null;
  sink_line?: number | null;
}

export interface TaintEvidenceResponse {
  status: string;
  schema_version?: string;
  artifact_id?: string;
  scan_id?: string;
  source_count: number;
  sink_count: number;
  sanitizer_count?: number;
  attack_path_count?: number;
  paths: TaintPathEvidence[];
  message?: string;
}

// ── Phase 3: Repositories & VCS ──────────────────────────────

export type RepositoryProviderType = 'local_git' | 'github';
export type RepositoryStatus = 'connected' | 'syncing' | 'ready' | 'error' | 'disconnected';

export interface RepositoryBranch {
  id: string;
  repository_id: string;
  name: string;
  commit_sha: string;
  is_default: boolean;
  last_seen_at: string;
  created_at: string;
}

export interface RepositoryCommit {
  id: string;
  repository_id: string;
  commit_sha: string;
  short_sha: string;
  parent_shas: string[];
  message: string;
  author_name: string | null;
  author_email: string | null;
  committed_at: string;
}

export interface Repository {
  id: string;
  project_id: string;
  provider: RepositoryProviderType;
  repo_url: string;
  display_name: string;
  default_branch: string;
  selected_branch: string;
  current_commit_sha: string | null;
  status: RepositoryStatus;
  last_synced_at: string | null;
  disconnected_at: string | null;
  created_at: string;
  updated_at: string;
  branches?: RepositoryBranch[];
}

// ── Phase 3: Source Snapshots & Preprocessing ────────────────

export type SourceType = 'upload' | 'git' | 'github';
export type SnapshotStatus = 'pending' | 'processing' | 'ready' | 'failed';
export type ValidationStatus = 'valid' | 'invalid' | 'warning';
export type PreprocessingStatus = 'pending' | 'completed' | 'failed' | 'skipped';

export interface SourceSnapshot {
  id: string;
  public_id: string;
  project_id: string;
  repository_id: string | null;
  repository_commit_id: string | null;
  source_type: SourceType;
  source_version: string | null;
  commit_sha: string | null;
  status: SnapshotStatus;
  content_hash: string;
  artifact_uri: string;
  manifest_uri: string | null;
  file_count: number;
  total_bytes: number;
  detected_languages: Record<string, number>;
  preprocessing_version: string;
  error_message: string | null;
  created_by: string;
  created_at: string;
  completed_at: string | null;
}

export interface SourceFile {
  id: string;
  source_snapshot_id: string;
  relative_path: string;
  language: string | null;
  size_bytes: number;
  content_hash: string;
  original_artifact_uri: string;
  normalized_artifact_uri: string | null;
  token_artifact_uri: string | null;
  line_count: number;
  is_binary: boolean;
  is_generated: boolean;
  classification: string;
  validation_status: ValidationStatus;
  preprocessing_status: PreprocessingStatus;
  created_at: string;
  function_count?: number;
}

export interface SourceFileContent {
  id: string;
  relative_path: string;
  language: string | null;
  size_bytes: number;
  line_count: number;
  content: string;
  content_hash: string;
  is_truncated: boolean;
}

export interface FunctionModel {
  id: string;
  source_file_id: string;
  function_id: string;
  name: string;
  qualified_name: string | null;
  language: string;
  start_line: number;
  end_line: number;
  signature: string | null;
  token_count: number;
  duplicate_group_id: string | null;
  extraction_status: string;
  created_at: string;
}

// ── Scan Results (Vulnerabilities) ───────────────────────────

export type VulnerabilitySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'SAFE';

export interface ScanResult {
  id: string;
  scan_id: string;
  file_path: string;
  function_name: string | null;
  line_number: number | null;
  severity: VulnerabilitySeverity;
  confidence: number;
  cwe_id: string | null;
  explanation: string | null;
  recommended_patch: string | null;
  model_version: string | null;
  created_at: string;
}

// Alias for UI compatibility
export interface Vulnerability {
  id: string;
  scan_id: string;
  title: string;
  description: string;
  severity: VulnerabilitySeverity;
  cvss_score: number;
  cwe_id: string;
  cwe_name: string;
  confidence: number;
  file_path: string;
  line_number: number;
  code_snippet: string;
  root_cause: string;
  suggested_fix?: string;
  is_fixed: boolean;
}

// ── Reports (Phase 7) ────────────────────────────────────────

export interface ReportFile {
  id: string;
  report_id: string;
  format: 'pdf' | 'html' | 'json' | 'csv';
  storage_key: string;
  content_type: string;
  size_bytes: number;
  checksum_sha256: string;
  created_at: string;
}

export interface Report {
  id: string;
  public_id: string;
  scan_id: string;
  project_id?: string;
  organization_id?: string;
  created_by?: string;
  report_type: 'developer' | 'security' | 'executive';
  format: 'pdf' | 'html' | 'json' | 'csv';
  status: 'pending' | 'queued' | 'generating' | 'completed' | 'failed';
  file_path: string | null;
  generated_at?: string | null;
  error_message?: string | null;
  config?: Record<string, any> | null;
  created_at: string;
  files?: ReportFile[];
}

// ── Notifications (Phase 7) ──────────────────────────────────

export interface Notification {
  id: string;
  public_id?: string;
  organization_id?: string;
  title: string;
  message?: string;
  body?: string;
  read: boolean;
  type: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
  timestamp?: string;
  created_at: string;
  link?: string;
  link_url?: string;
  entity_type?: string;
  entity_id?: string;
}

// ── Analytics (Phase 7) ──────────────────────────────────────

export interface SecurityHealthScore {
  score: number | null;
  rating: 'A' | 'B' | 'C' | 'D' | 'F' | null;
  status?: string;
  message?: string;
  version: string;
  weights?: Record<string, number>;
  penalties?: Record<string, number>;
  recovery_bonus?: number;
}

export interface AnalyticsMetrics {
  total_findings: number;
  active_findings: number;
  resolved_findings: number;
  critical_findings: number;
  severity_breakdown: Record<string, number>;
  cwe_distribution: Array<{ cwe_id: string; count: number }>;
  risk_trend: Array<{ date: string; avg_risk_score: number; active_findings: number }>;
  finding_trend?: Array<{ date: string; new_findings: number; fixed_findings: number }>;
  mttr_hours: number | null;
  remediation_rate: number;
  false_positive_rate: number;
  scan_success_rate?: number;
  health_score: SecurityHealthScore;
}

export interface ScanComparisonResult {
  baseline_scan: {
    id: string;
    public_id: string;
    completed_at?: string;
    created_at?: string;
  } | null;
  current_scan: {
    id: string;
    public_id: string;
    completed_at?: string;
    created_at?: string;
  };
  existing_count: number;
  new_count: number;
  fixed_count: number;
  existing_findings: Array<{ id: string; public_id: string; title: string; severity: string; fingerprint: string }>;
  new_findings: Array<{ id: string; public_id: string; title: string; severity: string; fingerprint: string }>;
  fixed_findings: Array<{ id: string; public_id: string; title: string; severity: string; fingerprint: string }>;
}

export interface DashboardMetrics {
  total_projects: number;
  total_scans: number;
  completed_scans?: number;
  failed_scans?: number;
  total_vulnerabilities: number;
  severity_breakdown: Record<string, number>;
  recent_scans: Scan[];
  scan_success_rate?: number;
  vulnerabilities_by_cwe?: Array<{ cwe_id: string; count: number }>;
  health_score?: number | null | SecurityHealthScore;
  health_rating?: string | null;
  health_status?: string;
  score_version?: string;
  active_findings?: number;
}

// ── PR Security & Gates (Phase 7) ────────────────────────────

export interface SecurityGatePolicy {
  id: string;
  project_id: string;
  block_new_critical: boolean;
  block_new_high: boolean;
  block_secrets: boolean;
  cvss_threshold: number | null;
  version: string;
  updated_at?: string;
}

export interface PRSecurityResult {
  id: string;
  public_id: string;
  project_id: string;
  repository_id: string;
  pull_request_number: number;
  pr_head_sha: string;
  pr_base_sha?: string | null;
  pr_branch?: string | null;
  pr_title?: string | null;
  baseline_scan_id?: string | null;
  pr_scan_id: string;
  existing_count: number;
  new_count: number;
  fixed_count: number;
  gate_result: 'PASS' | 'FAIL' | 'SKIPPED';
  status: 'completed' | 'failed' | 'running';
  summary?: string | null;
  created_at: string;
  completed_at?: string | null;
}

// ── API Response Envelope ────────────────────────────────────

export interface ApiResponse<T = unknown> {
  status: 'success' | 'error';
  data: T;
  message: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface PaginatedResponse<T> {
  status: 'success' | 'error';
  data: PaginatedData<T>;
  message: string;
}

// ── Phase 5 Findings ─────────────────────────────────────────
export * from './types/finding';

// ── Phase 6 Remediation & XAI ────────────────────────────────
export * from './types/remediation';


