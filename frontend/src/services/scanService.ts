// ============================================================
// Scan Service — Scan Execution & Status
// ============================================================

import apiClient from './api';
import { Scan, ScanStatusInfo, PaginatedData } from '../types';

export const scanService = {
  async createScan(data: {
    project_id: string;
    upload_id?: string;
    repository_id?: string;
  }): Promise<Scan> {
    const { data: scan } = await apiClient.post<Scan>('/scans', data);
    return scan;
  },

  async listScans(params?: {
    project_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedData<Scan>> {
    const { data } = await apiClient.get<PaginatedData<Scan>>('/scans', {
      params,
    });
    return data;
  },

  async getScan(scanId: string): Promise<Scan> {
    const { data } = await apiClient.get<Scan>(`/scans/${scanId}`);
    return data;
  },

  async getScanStatus(scanId: string): Promise<ScanStatusInfo> {
    const { data } = await apiClient.get<ScanStatusInfo>(
      `/scans/${scanId}/status`
    );
    return data;
  },

  async cancelScan(scanId: string): Promise<void> {
    await apiClient.post(`/scans/${scanId}/cancel`);
  },
};
