// ============================================================
// Analytics Service (Phase 7) — Authoritative Aggregations
// ============================================================

import apiClient from './api';
import { AnalyticsMetrics, DashboardMetrics, ScanComparisonResult } from '../types';

export interface AnalyticsQueryParams {
  from_date?: string;
  to_date?: string;
  project_id?: string;
}

export const analyticsService = {
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const { data } = await apiClient.get<DashboardMetrics>('/analytics/dashboard');
    return data;
  },

  async getOrganizationAnalytics(params?: AnalyticsQueryParams): Promise<AnalyticsMetrics> {
    const { data } = await apiClient.get<AnalyticsMetrics>('/analytics', { params });
    return data;
  },

  async getProjectAnalytics(projectId: string, params?: AnalyticsQueryParams): Promise<AnalyticsMetrics> {
    const { data } = await apiClient.get<AnalyticsMetrics>(`/projects/${projectId}/analytics`, { params });
    return data;
  },

  async compareScans(projectId: string, scanAId: string, scanBId: string): Promise<ScanComparisonResult> {
    const { data } = await apiClient.get<ScanComparisonResult>(
      `/projects/${projectId}/analytics/compare?scan_a_id=${encodeURIComponent(scanAId)}&scan_b_id=${encodeURIComponent(scanBId)}&baseline_scan_id=${encodeURIComponent(scanAId)}&current_scan_id=${encodeURIComponent(scanBId)}`
    );
    return data;
  },
};
