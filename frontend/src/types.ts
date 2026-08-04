export interface User {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  role: 'admin' | 'developer' | 'viewer';
}

export interface Project {
  id: string;
  name: string;
  description: string;
  language: string;
  visibility: 'private' | 'public' | 'internal';
  repository_url?: string;
  last_scan_at?: string;
  risk_score: number;
  status: 'active' | 'archived';
  created_at: string;
}

export type ScanStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface Scan {
  id: string;
  job_id: string;
  project_id: string;
  status: ScanStatus;
  progress: number;
  started_at: string;
  completed_at?: string;
  summary?: {
    total_files: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
    safe: number;
  };
}

export type VulnerabilitySeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'SAFE';

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

export interface Notification {
  id: string;
  title: string;
  message: string;
  read: boolean;
  type: 'info' | 'success' | 'warning' | 'error';
  timestamp: string;
  link?: string;
}

export interface AnalyticsSummary {
  total_projects: number;
  total_scans_this_month: number;
  avg_risk_score: number;
  vulnerabilities_by_severity: Record<string, number>;
  top_cwe: Array<{ cwe: string; count: number }>;
}
