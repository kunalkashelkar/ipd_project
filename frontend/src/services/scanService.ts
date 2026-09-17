// ============================================================
// Scan Service — Scan Execution, Lifecycle & Artifacts (Phase 4)
// ============================================================

import apiClient from './api';
import {
  Scan,
  ScanStatusInfo,
  ScanStageRun,
  AnalysisArtifact,
  TaintEvidenceResponse,
  PaginatedData,
} from '../types';

export const scanService = {
  async createScan(data: {
    project_id: string;
    upload_id?: string;
    repository_id?: string;
    source_snapshot_id?: string;
    idempotency_key?: string;
    config?: Record<string, any>;
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

  async getScanStages(scanId: string): Promise<ScanStageRun[]> {
    const { data } = await apiClient.get<ScanStageRun[]>(
      `/scans/${scanId}/stages`
    );
    return data;
  },

  async getScanArtifacts(scanId: string): Promise<AnalysisArtifact[]> {
    const { data } = await apiClient.get<AnalysisArtifact[]>(
      `/scans/${scanId}/artifacts`
    );
    return data;
  },

  async getArtifactDownload(
    scanId: string,
    artifactId: string
  ): Promise<{ artifact: AnalysisArtifact; download_url: string }> {
    const { data } = await apiClient.get<{
      artifact: AnalysisArtifact;
      download_url: string;
    }>(`/scans/${scanId}/artifacts/${artifactId}/download`);
    return data;
  },

  async downloadArtifact(scanId: string, artifactId: string): Promise<Blob> {
    const response = await apiClient.get<Blob>(
      `/scans/${scanId}/artifacts/${artifactId}/download`,
      {
        responseType: 'blob',
      }
    );
    return response.data;
  },


  async getTaintEvidence(scanId: string): Promise<TaintEvidenceResponse> {
    const { data } = await apiClient.get<TaintEvidenceResponse>(
      `/scans/${scanId}/taint-evidence`
    );
    return data;
  },

  async cancelScan(scanId: string): Promise<void> {
    await apiClient.post(`/scans/${scanId}/cancel`);
  },

  async retryScan(scanId: string): Promise<Scan> {
    const { data } = await apiClient.post<Scan>(`/scans/${scanId}/retry`);
    return data;
  },
};
