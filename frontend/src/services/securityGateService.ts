// ============================================================
// Security Gate Service (Phase 7) — PR Security & Gate Policy
// ============================================================

import apiClient from './api';
import { PRSecurityResult, SecurityGatePolicy } from '../types';

export const securityGateService = {
  async getGatePolicy(projectId: string): Promise<SecurityGatePolicy> {
    const { data } = await apiClient.get<SecurityGatePolicy>(
      `/projects/${projectId}/gate-policy`
    );
    return data;
  },

  async updateGatePolicy(
    projectId: string,
    policy: Partial<SecurityGatePolicy>
  ): Promise<SecurityGatePolicy> {
    const { data } = await apiClient.put<SecurityGatePolicy>(
      `/projects/${projectId}/gate-policy`,
      policy
    );
    return data;
  },

  async getPRSecurityResults(projectId: string): Promise<PRSecurityResult[]> {
    const { data } = await apiClient.get<any>(
      `/projects/${projectId}/pr-results`
    );
    return data.items || data;
  },

  async getPRSecurityResult(
    projectId: string,
    resultId: string
  ): Promise<PRSecurityResult> {
    const { data } = await apiClient.get<PRSecurityResult>(
      `/projects/${projectId}/pr-results/${resultId}`
    );
    return data;
  },
};
