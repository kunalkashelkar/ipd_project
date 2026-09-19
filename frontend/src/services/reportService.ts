// ============================================================
// Report Service (Phase 7) — Async Reports & File Downloads
// ============================================================

import apiClient from './api';
import { PaginatedData, Report } from '../types';

export interface ReportCreateParams {
  scan_id: string;
  report_type: 'developer' | 'security' | 'executive';
  format: 'pdf' | 'html' | 'json' | 'csv';
}

export interface ReportFilterParams {
  project_id?: string;
  scan_id?: string;
  report_type?: string;
  format?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export const reportService = {
  async getReports(params?: ReportFilterParams): Promise<PaginatedData<Report>> {
    const { data } = await apiClient.get<PaginatedData<Report>>('/reports', { params });
    return data;
  },

  async getReport(reportId: string): Promise<Report> {
    const { data } = await apiClient.get<Report>(`/reports/${reportId}`);
    return data;
  },

  async requestReport(params: ReportCreateParams): Promise<Report> {
    const { data } = await apiClient.post<Report>('/reports', params);
    return data;
  },

  async retryReport(reportId: string): Promise<Report> {
    const { data } = await apiClient.post<Report>(`/reports/${reportId}/retry`);
    return data;
  },

  async downloadReport(reportId: string, filename: string): Promise<void> {
    const response = await apiClient.get(`/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    const blob = new Blob([response.data], {
      type: (response.headers['content-type'] as string) || 'application/octet-stream',
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
