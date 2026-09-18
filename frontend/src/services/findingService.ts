// ============================================================
// Finding Service — Vulnerability Investigation & Management (Phase 5)
// ============================================================

import apiClient from './api';
import {
  FindingListItem,
  FindingDetail,
  FindingOccurrence,
  FindingStatusHistory,
  FindingComment,
  FindingAssignment,
  FindingSuppression,
  ProjectFindingsSummary,
  GlobalFindingsSummary,
  FindingSourceContext,
  PaginatedData,
} from '../types';

export const findingService = {
  async getGlobalFindings(
    params?: {
      severity?: string;
      status?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PaginatedData<FindingListItem>> {
    const { data } = await apiClient.get<PaginatedData<FindingListItem>>(
      `/findings`,
      { params }
    );
    return data;
  },

  async getGlobalFindingsSummary(): Promise<GlobalFindingsSummary> {
    const { data } = await apiClient.get<GlobalFindingsSummary>(`/findings/summary`);
    return data;
  },

  async getProjectFindings(
    projectId: string,
    params?: {
      severity?: string;
      status?: string;
      cwe?: string;
      search?: string;
      sort_by?: string;
      sort_order?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PaginatedData<FindingListItem>> {
    const { data } = await apiClient.get<PaginatedData<FindingListItem>>(
      `/projects/${projectId}/findings`,
      { params }
    );
    return data;
  },

  async getProjectFindingsSummary(projectId: string): Promise<ProjectFindingsSummary> {
    const { data } = await apiClient.get<ProjectFindingsSummary>(
      `/projects/${projectId}/findings/summary`
    );
    return data;
  },

  async getScanFindings(scanId: string): Promise<FindingListItem[]> {
    const { data } = await apiClient.get<FindingListItem[]>(`/scans/${scanId}/findings`);
    return data;
  },

  async getFindingDetail(findingId: string): Promise<FindingDetail> {
    const { data } = await apiClient.get<FindingDetail>(`/findings/${findingId}`);
    return data;
  },

  async getFindingSourceContext(
    findingId: string,
    windowLines: number = 15
  ): Promise<FindingSourceContext> {
    const { data } = await apiClient.get<FindingSourceContext>(
      `/findings/${findingId}/source`,
      { params: { window: windowLines } }
    );
    return data;
  },

  async transitionStatus(
    findingId: string,
    payload: { status: string; reason?: string }
  ): Promise<FindingStatusHistory> {
    const { data } = await apiClient.post<FindingStatusHistory>(
      `/findings/${findingId}/status`,
      payload
    );
    return data;
  },

  async assignFinding(
    findingId: string,
    payload: { user_id: string }
  ): Promise<FindingAssignment> {
    const { data } = await apiClient.post<FindingAssignment>(
      `/findings/${findingId}/assign`,
      payload
    );
    return data;
  },

  async addComment(
    findingId: string,
    payload: { content: string }
  ): Promise<FindingComment> {
    const { data } = await apiClient.post<FindingComment>(
      `/findings/${findingId}/comments`,
      payload
    );
    return data;
  },

  async getComments(findingId: string): Promise<FindingComment[]> {
    const { data } = await apiClient.get<FindingComment[]>(
      `/findings/${findingId}/comments`
    );
    return data;
  },

  async suppressFinding(
    findingId: string,
    payload: {
      suppression_type: 'FALSE_POSITIVE' | 'RISK_ACCEPTED' | 'SUPPRESSED';
      reason: string;
      expires_at?: string;
    }
  ): Promise<FindingSuppression> {
    const { data } = await apiClient.post<FindingSuppression>(
      `/findings/${findingId}/suppress`,
      payload
    );
    return data;
  },

  async unsuppressFinding(findingId: string): Promise<void> {
    await apiClient.post(`/findings/${findingId}/unsuppress`);
  },
};
