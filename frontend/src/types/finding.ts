// ============================================================
// Finding Domain Types (Phase 5)
// ============================================================

export interface AIPrediction {
  id: string;
  scan_id: string;
  source_snapshot_id: string;
  file_path: string;
  function_name?: string | null;
  line_number?: number | null;
  end_line?: number | null;
  prediction: string;
  confidence: number;
  cwe_id?: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low';
  cvss_score?: number | null;
  evidence_json?: Record<string, any> | null;
  provider: string;
  model_name: string;
  model_version: string;
  generated_by_ai: boolean;
  created_at: string;
}

export interface FindingOccurrence {
  id: string;
  finding_id: string;
  scan_id: string;
  source_snapshot_id: string;
  file_path: string;
  function_name?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  location?: Record<string, any> | null;
  ai_prediction_id?: string | null;
  static_evidence_ref?: Record<string, any> | null;
  taint_evidence_ref?: Record<string, any> | null;
  graph_evidence_ref?: Record<string, any> | null;
  confidence: number;
  severity: string;
  observed_at: string;
  ai_prediction?: AIPrediction | null;
}

export interface FindingStatusHistory {
  id: string;
  finding_id: string;
  previous_status?: string | null;
  new_status: string;
  actor_id?: string | null;
  reason?: string | null;
  change_metadata?: Record<string, any> | null;
  created_at: string;
}

export interface FindingAssignment {
  id: string;
  finding_id: string;
  assigned_to_user_id: string;
  assigned_by_user_id?: string | null;
  active: boolean;
  created_at: string;
}

export interface FindingComment {
  id: string;
  finding_id: string;
  author_id: string;
  content: string;
  created_at: string;
  updated_at?: string | null;
}

export interface FindingSuppression {
  id: string;
  finding_id: string;
  actor_id: string;
  suppression_type: 'FALSE_POSITIVE' | 'RISK_ACCEPTED' | 'SUPPRESSED';
  reason: string;
  expires_at?: string | null;
  active: boolean;
  created_at: string;
}

export interface FindingListItem {
  id: string;
  public_id?: string;
  project_id: string;
  project_public_id?: string;
  project_name?: string;
  latest_scan_id?: string;
  latest_scan_public_id?: string;
  scan_public_id?: string;
  latest_scan_status?: string;
  organization_id: string;
  title: string;
  vulnerability_type: string;
  cwe_id?: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low';
  cvss_score?: number | null;
  confidence: number;
  risk_score: number;
  status: string;
  fingerprint: string;
  first_seen_at: string;
  last_seen_at: string;
  fixed_at?: string | null;
  latest_file_path?: string | null;
  latest_line_number?: number | null;
  occurrence_count: number;
}

export interface FindingDetail {
  id: string;
  public_id?: string;
  project_id: string;
  project_public_id?: string;
  project_name?: string;
  organization_id: string;
  title: string;
  vulnerability_type: string;
  cwe_id?: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low';
  cvss_score?: number | null;
  confidence: number;
  risk_score: number;
  risk_version: string;
  status: string;
  fingerprint: string;
  fingerprint_version: string;
  first_seen_at: string;
  last_seen_at: string;
  fixed_at?: string | null;
  created_at: string;
  updated_at: string;
  latest_occurrence?: FindingOccurrence | null;
  occurrences: FindingOccurrence[];
  status_history: FindingStatusHistory[];
  assignments: FindingAssignment[];
  comments: FindingComment[];
  suppressions: FindingSuppression[];
}

export interface ProjectFindingsSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  open: number;
  confirmed: number;
  in_progress: number;
  fixed: number;
  suppressed: number;
  false_positive: number;
  risk_accepted: number;
}

export interface GlobalFindingsSummary {
  total: number;
  open: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  fixed: number;
  suppressed: number;
}

export interface FindingSourceContext {
  file_path: string;
  language?: string | null;
  line_number?: number | null;
  start_line: number;
  end_line: number;
  source_snippet: string;
  snapshot_id: string;
  is_snapshot_immutable: boolean;
}
