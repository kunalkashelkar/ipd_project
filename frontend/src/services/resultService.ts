// ============================================================
// Result Service — Vulnerability Findings
// ============================================================

import apiClient from './api';
import { ScanResult, PaginatedData } from '../types';

export const resultService = {
  async getScanResults(
    scanId: string,
    params?: {
      severity?: string;
      page?: number;
      page_size?: number;
    }
  ): Promise<PaginatedData<ScanResult>> {
    const { data } = await apiClient.get<PaginatedData<ScanResult>>(
      `/results/scans/${scanId}`,
      { params }
    );
    return data;
  },

  async getScanSummary(
    scanId: string
  ): Promise<Record<string, number>> {
    const { data } = await apiClient.get<Record<string, number>>(
      `/results/scans/${scanId}/summary`
    );
    return data;
  },

  async submitFeedback(
    resultId: string,
    isCorrect: boolean,
    comment?: string
  ): Promise<unknown> {
    const { data } = await apiClient.post(`/results/${resultId}/feedback`, {
      is_correct: isCorrect,
      comment,
    });
    return data;
  },
};
