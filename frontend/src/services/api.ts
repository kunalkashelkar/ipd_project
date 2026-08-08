// ============================================================
// API Client — Axios with JWT Interceptor & Response Unwrapper
// ============================================================

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// ── Create Axios Instance ────────────────────────────────────

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor: Attach JWT Token ────────────────────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Read token from persisted Zustand store in localStorage
    try {
      const raw = localStorage.getItem('auth-storage');
      if (raw) {
        const parsed = JSON.parse(raw);
        const token = parsed?.state?.token;
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch {
      // Silently ignore parse errors
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Unwrap Envelope & Handle 401 ───────

apiClient.interceptors.response.use(
  (response) => {
    // The backend wraps responses in { status, data, message }
    // We unwrap so consumers get the inner `data` directly
    if (response.data && response.data.status === 'success') {
      response.data = response.data.data;
    }
    return response;
  },
  (error: AxiosError<{ status: string; message: string; detail?: string }>) => {
    if (error.response) {
      const status = error.response.status;
      const message =
        error.response.data?.message ||
        error.response.data?.detail ||
        'An unexpected error occurred';

      if (status === 401) {
        // Clear auth state and redirect to login
        try {
          localStorage.removeItem('auth-storage');
        } catch { /* ignore */ }
        
        // Only redirect if not already on login/register page
        if (!window.location.pathname.startsWith('/login') &&
            !window.location.pathname.startsWith('/register')) {
          toast.error('Session expired. Please log in again.');
          window.location.href = '/login';
        }
      } else if (status === 403) {
        toast.error('Access denied: ' + message);
      } else if (status === 422) {
        toast.error('Validation error: ' + message);
      } else if (status >= 500) {
        toast.error('Server error: ' + message);
      }
    } else if (error.request) {
      toast.error('Network error. Please check your connection.');
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// ── Legacy API functions (kept for backward compatibility) ────

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

// Legacy API calls using the new apiClient
export const uploadFile = async (file: File): Promise<UploadResponse> => {
  const form = new FormData();
  form.append('file', file);
  const { data } = await apiClient.post<UploadResponse>('/upload', form);
  return data;
};

export const queueParse = async (
  uploadId: string,
  projectId?: string,
): Promise<ParseJobResponse> => {
  const { data } = await apiClient.post<ParseJobResponse>('/parse', {
    upload_id: uploadId,
    project_id: projectId ?? null,
  });
  return data;
};

export const getParseStatus = async (jobId: string): Promise<ParseStatusResponse> => {
  const { data } = await apiClient.get<ParseStatusResponse>(`/parse/${jobId}`);
  return data;
};

export const getGraph = async (jobId: string): Promise<GraphResponse> => {
  const { data } = await apiClient.get<GraphResponse>(`/parse/${jobId}/graph`);
  return data;
};

export const checkHealth = async () => {
  // Health endpoint is outside /api/v1
  const { data } = await axios.get('/health');
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
  const { data } = await apiClient.post<TaintJobResponse>('/taint/analyze', {
    cpg_job_id: cpgJobId,
    project_id: projectId ?? null,
  });
  return data;
};

export const getTaintStatus = async (taintJobId: string): Promise<TaintStatusResponse> => {
  const { data } = await apiClient.get<TaintStatusResponse>(`/taint/${taintJobId}`);
  return data;
};

export const getTaintReport = async (taintJobId: string): Promise<TaintReportResponse> => {
  const { data } = await apiClient.get<TaintReportResponse>(`/taint/${taintJobId}/report`);
  return data;
};

export const getTaintGraph = async (taintJobId: string): Promise<GraphResponse> => {
  const { data } = await apiClient.get<GraphResponse>(`/taint/${taintJobId}/graph`);
  return data;
};
