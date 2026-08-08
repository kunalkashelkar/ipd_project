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
  tokens: TokenPair;
}

// ── Projects ─────────────────────────────────────────────────

export interface Project {
  id: string;
  name: string;
  description: string | null;
  language: string | null;
  default_branch: string | null;
  owner_id: string;
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
  | 'queued'
  | 'preprocessing'
  | 'ai_running'
  | 'storing_results'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'running';

export interface Scan {
  id: string;
  project_id: string;
  upload_id: string | null;
  repository_id: string | null;
  user_id: string;
  status: ScanStatus;
  progress: number;
  current_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ScanStatusInfo {
  id: string;
  status: ScanStatus;
  progress: number;
  current_stage: string | null;
  error_message: string | null;
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

// ── Reports ──────────────────────────────────────────────────

export interface Report {
  id: string;
  scan_id: string;
  format: string;
  status: string;
  file_path: string | null;
  created_at: string;
}

// ── Notifications ────────────────────────────────────────────

export interface Notification {
  id: string;
  title: string;
  message: string;
  read: boolean;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
  link?: string;
}

// ── Analytics ────────────────────────────────────────────────

export interface DashboardMetrics {
  total_projects: number;
  total_scans: number;
  total_vulnerabilities: number;
  severity_breakdown: Record<string, number>;
  recent_scans: Scan[];
}

export interface AnalyticsSummary {
  total_projects: number;
  total_scans_this_month: number;
  avg_risk_score: number;
  vulnerabilities_by_severity: Record<string, number>;
  top_cwe: Array<{ cwe: string; count: number }>;
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
