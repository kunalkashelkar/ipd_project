// ============================================================
// Canonical API Client — Axios with Auth Storage & Normalization
// ============================================================

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import toast from 'react-hot-toast';
import { authStorage } from './authStorage';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// ── Create Axios Instance ────────────────────────────────────

const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor: Attach JWT Token via authStorage ────

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = authStorage.getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    const orgId = authStorage.getActiveOrganizationId();
    if (orgId && config.headers && !config.headers['X-Organization-ID']) {
      config.headers['X-Organization-ID'] = orgId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: Unwrap Envelope & Handle Errors ─────

export interface ApiErrorPayload {
  status: 'error';
  message: string;
  detail?: string;
  details?: Array<{ field?: string; message: string }>;
}

apiClient.interceptors.response.use(
  (response) => {
    // Standard backend wraps responses in { status, data, message }
    // Unwrap envelope so consumers receive data directly
    if (response.data && response.data.status === 'success') {
      response.data = response.data.data;
    }
    return response;
  },
  (error: AxiosError<ApiErrorPayload>) => {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;
      const structError = (data as any)?.error;
      const errorList = (data as any)?.errors || structError?.details;
      const specificFieldErr = Array.isArray(errorList) && errorList.length > 0 ? `${errorList[0].message} on ${errorList[0].field}` : null;
      const message =
        (structError?.message && structError.message !== 'Validation failed')
          ? structError.message
          : specificFieldErr && (!data?.message || data.message === 'Validation failed')
          ? `Validation failed: ${specificFieldErr}`
          : data?.message ||
            data?.detail ||
            (Array.isArray(data?.details) && data.details[0]?.message) ||
            'An unexpected error occurred';

      if (status === 401) {
        authStorage.clearSession();
        // Redirect to login if not already on public auth or onboarding pages
        if (
          !window.location.pathname.startsWith('/login') &&
          !window.location.pathname.startsWith('/register') &&
          !window.location.pathname.startsWith('/forgot-password') &&
          !window.location.pathname.startsWith('/reset-password') &&
          !window.location.pathname.startsWith('/invitations') &&
          !window.location.pathname.startsWith('/invite') &&
          window.location.pathname !== '/'
        ) {
          toast.error('Session expired. Please sign in again.');
          window.location.href = '/login';
        }
      } else if (status === 403) {
        toast.error(`Access denied: ${message}`, { id: `access-denied-${message}` });
      } else if (status === 404) {
        // Handled by pages or caught by caller
      } else if (status === 409) {
        toast.error(`Conflict: ${message}`, { id: `conflict-${message}` });
      } else if (status === 422) {
        toast.error(`Validation error: ${message}`, { id: `validation-${message}` });
      } else if (status >= 500) {
        toast.error(`Server error: ${message}`, { id: `server-error-${message}` });
      }
    } else if (error.request) {
      toast.error('Network error. Please check your connection.', { id: 'network-error' });
    }

    return Promise.reject(error);
  }
);

export default apiClient;

// ── System Health API ────────────────────────────────────────

export const checkHealth = async () => {
  const { data } = await axios.get('/health');
  return data;
};

export const checkReadiness = async () => {
  const { data } = await axios.get('/health/ready');
  return data;
};
