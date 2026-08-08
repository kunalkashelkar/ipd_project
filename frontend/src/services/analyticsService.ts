// ============================================================
// Analytics Service — Dashboard Metrics
// ============================================================

import apiClient from './api';
import { DashboardMetrics } from '../types';

export const analyticsService = {
  async getDashboardMetrics(): Promise<DashboardMetrics> {
    const { data } = await apiClient.get<DashboardMetrics>(
      '/analytics/dashboard'
    );
    return data;
  },
};
