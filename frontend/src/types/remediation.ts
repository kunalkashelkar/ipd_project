// ============================================================
// Remediation, XAI & Validation Types (Phase 6)
// ============================================================

export interface ImportantLocation {
  file: string;
  start_line: number;
  end_line: number;
  importance: number;
}

export interface ImportantToken {
  token: string;
  importance: number;
  line_number?: number | null;
}

export interface ImportantGraphNode {
  node_id: string;
  label: string;
  node_type: string;
  importance: number;
}

export interface ImportantGraphEdge {
  source: string;
  target: string;
  edge_type: string;
  importance: number;
}

export interface AIExplanation {
  id: string;
  finding_id: string;
  prediction_id?: string | null;
  source_snapshot_id: string;
  organization_id: string;
  project_id: string;

  provider: string;
  model_name: string;
  model_version: string;
  explanation_method: string;
  schema_version: string;

  summary: string;
  root_cause: string;
  why_vulnerable: string;
  impact: string;
  evidence_explanation: string;
  warnings: string[];
  confidence?: number | null;
  generated_by_ai: boolean;

  artifact_uri?: string | null;
  checksum?: string | null;

  important_locations: ImportantLocation[];
  important_tokens: ImportantToken[];
  important_functions: Array<Record<string, any>>;
  important_nodes: ImportantGraphNode[];
  important_edges: ImportantGraphEdge[];

  method_status: 'SUPPORTED' | 'NOT_SUPPORTED' | 'FAILED' | 'MODEL_NOT_READY';
  status_reason?: string | null;
  created_at: string;
}

export interface RemediationValidation {
  id: string;
  remediation_id: string;
  finding_id: string;
  source_snapshot_id: string;
  organization_id: string;
  project_id: string;

  attempt_number: number;
  workspace_identifier: string;
  validation_policy_version: string;
  status: 'PREPARING' | 'RUNNING' | 'PASSED' | 'FAILED' | 'TIMED_OUT';
  started_at: string;
  completed_at?: string | null;
  timeout_seconds: number;

  patch_apply_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED';
    message?: string;
    changed_files?: string[];
  };
  syntax_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED' | 'NOT_CONFIGURED';
    message?: string;
  };
  build_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED' | 'NOT_CONFIGURED';
    message?: string;
  };
  test_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED' | 'NOT_CONFIGURED';
    message?: string;
  };
  static_analysis_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED';
    issue_still_present?: boolean;
    message?: string;
  };
  taint_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED' | 'UNSUPPORTED';
    message?: string;
  };
  graph_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED' | 'UNSUPPORTED';
    message?: string;
  };
  regression_result: {
    status?: 'PASS' | 'FAIL' | 'SKIPPED';
    message?: string;
    regressions_detected?: boolean;
  };

  verification_scan_id?: string | null;
  final_verification_result: 'VERIFIED' | 'NOT_VERIFIED' | 'FAILED' | 'PENDING';
  failure_reason?: string | null;

  logs_artifact_uri?: string | null;
  artifact_checksum?: string | null;
  created_at: string;
}

export interface Remediation {
  id: string;
  finding_id: string;
  organization_id: string;
  project_id: string;
  source_snapshot_id: string;

  remediation_number: number;
  provider: string;
  model_name: string;
  model_version: string;
  prompt_version: string;
  status:
    | 'PROPOSED'
    | 'GENERATED'
    | 'APPROVED'
    | 'REJECTED'
    | 'APPLIED'
    | 'VALIDATING'
    | 'VALIDATED'
    | 'FAILED_VALIDATION'
    | 'SUPERSEDED';

  summary: string;
  explanation: string;
  diff_content: string;
  patch_artifact_uri?: string | null;
  patch_checksum: string;
  changed_files: string[];

  confidence?: number | null;
  warnings: string[];
  generated_by_ai: boolean;
  is_active_candidate: boolean;

  created_by_user_id?: string | null;
  reviewed_by_user_id?: string | null;
  reviewed_at?: string | null;
  review_comment?: string | null;
  superseded_by_id?: string | null;

  created_at: string;
  updated_at: string;

  validations?: RemediationValidation[];
}

export interface VerificationStatus {
  finding_id: string;
  finding_status: string;
  is_verified: boolean;
  active_remediation_id?: string | null;
  active_remediation_status?: string | null;
  latest_validation_id?: string | null;
  latest_validation_status?: string | null;
  verification_scan_id?: string | null;
  final_verification_result?: string | null;
  verified_at?: string | null;
  verification_details: {
    patch_apply?: string | null;
    syntax?: string | null;
    build?: string | null;
    tests?: string | null;
    static_analysis?: string | null;
    taint?: string | null;
    regression?: string | null;
  };
}

export interface ModelVersion {
  id: string;
  model_name: string;
  version: string;
  provider: string;
  artifact_uri?: string | null;
  checksum?: string | null;
  runtime: string;
  input_schema_version: string;
  output_schema_version: string;
  status: 'active' | 'inactive' | 'deprecated' | 'unavailable';
  metadata_json?: Record<string, any> | null;
  activated_at?: string | null;
  created_at: string;
  updated_at: string;
}
