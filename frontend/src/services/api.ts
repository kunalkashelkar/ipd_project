// API client — typed service layer for backend communication
import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({ baseURL: BASE });

// ── Types ───────────────────────────────────────────────────────

export interface UploadResponse {
  id: string;
  project_id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_extension: string;
  status: string;
  created_at: string;
}

export interface ParseJobResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ParseStatusResponse {
  job_id: string;
  project_id: string;
  status: string;
  file_count: number;
  function_count: number;
  ast_nodes: number;
  cfg_nodes: number;
  dfg_nodes: number;
  total_nodes: number;
  total_edges: number;
  graph_path: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface GraphNode {
  id: string;
  label?: string;
  code?: string;
  line_number?: number;
  filename?: string;
  layers?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  label?: string;
  layer?: string;
  variable?: string;
}

export interface GraphResponse {
  job_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  statistics: Record<string, unknown>;
}

// ── API calls ───────────────────────────────────────────────────

export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post<UploadResponse>('/upload', form);
  return data;
};

export const queueParse = async (
  uploadId: string,
  projectId?: string,
): Promise<ParseJobResponse> => {
  const { data } = await api.post<ParseJobResponse>('/parse', {
    upload_id: uploadId,
    project_id: projectId ?? null,
  });
  return data;
};

export const getParseStatus = async (jobId: string): Promise<ParseStatusResponse> => {
  const { data } = await api.get<ParseStatusResponse>(`/parse/${jobId}`);
  return data;
};

export const getGraph = async (jobId: string): Promise<GraphResponse> => {
  const { data } = await api.get<GraphResponse>(`/parse/${jobId}/graph`);
  return data;
};

export const checkHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};

// ── Taint Analysis ──────────────────────────────────────────────

export interface TaintJobResponse {
  taint_job_id: string;
  cpg_job_id: string;
  status: string;
  message: string;
}

export interface TaintStatusResponse {
  taint_job_id: string;
  cpg_job_id: string;
  status: string;
  source_count: number;
  sink_count: number;
  sanitizer_count: number;
  tainted_node_count: number;
  attack_path_count: number;
  critical_path_count: number;
  high_path_count: number;
  medium_path_count: number;
  low_path_count: number;
  security_graph_path: string | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface AttackPath {
  path_id: string;
  source_node_id: string;
  sink_node_id: string;
  nodes: string[];
  length: number;
  sanitized: boolean;
  severity: string;
  risk_score: number;
  sink_category: string;
  source_category: string;
  source_code: string;
  sink_code: string;
  source_line: number | null;
  sink_line: number | null;
  filename: string | null;
}

export interface TaintReportResponse {
  taint_job_id: string;
  cpg_job_id: string;
  summary: Record<string, number>;
  attack_paths: AttackPath[];
}

export const analyzeTaint = async (cpgJobId: string, projectId?: string): Promise<TaintJobResponse> => {
  const { data } = await api.post<TaintJobResponse>('/taint/analyze', {
    cpg_job_id: cpgJobId,
    project_id: projectId ?? null,
  });
  return data;
};

export const getTaintStatus = async (taintJobId: string): Promise<TaintStatusResponse> => {
  const { data } = await api.get<TaintStatusResponse>(`/taint/${taintJobId}`);
  return data;
};

export const getTaintReport = async (taintJobId: string): Promise<TaintReportResponse> => {
  const { data } = await api.get<TaintReportResponse>(`/taint/${taintJobId}/report`);
  return data;
};

export const getTaintGraph = async (taintJobId: string): Promise<GraphResponse> => {
  const { data } = await api.get<GraphResponse>(`/taint/${taintJobId}/graph`);
  return data;
};
