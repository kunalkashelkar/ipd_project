// ============================================================
// Remediation & XAI Service — Frontend API Client (Phase 6)
// ============================================================

import apiClient from './api';
import {
  AIExplanation,
  ModelVersion,
  Remediation,
  RemediationValidation,
  VerificationStatus,
} from '../types';

export const remediationService = {
  // ── Explanations & XAI ─────────────────────────────────────

  async getFindingExplanations(findingId: string, method?: string): Promise<AIExplanation[]> {
    const { data } = await apiClient.get<AIExplanation[]>(`/findings/${findingId}/explanation`, {
      params: method ? { method } : undefined,
    });
    return data;
  },

  async generateFindingExplanation(
    findingId: string,
    method: string = 'evidence_synthesizer'
  ): Promise<AIExplanation> {
    const { data } = await apiClient.post<AIExplanation>(`/findings/${findingId}/explanation`, {
      method,
    });
    return data;
  },

  // ── Remediations & Patches ─────────────────────────────────

  async getFindingRemediations(findingId: string): Promise<Remediation[]> {
    const { data } = await apiClient.get<Remediation[]>(`/findings/${findingId}/remediations`);
    return data;
  },

  async generateFindingRemediation(
    findingId: string,
    promptVersion: string = 'v1.0.0'
  ): Promise<Remediation> {
    const { data } = await apiClient.post<Remediation>(`/findings/${findingId}/remediations`, {
      prompt_version: promptVersion,
    });
    return data;
  },

  async getRemediationDetail(remediationId: string): Promise<Remediation> {
    const { data } = await apiClient.get<Remediation>(`/remediations/${remediationId}`);
    return data;
  },

  async reviewRemediation(
    remediationId: string,
    decision: 'APPROVE' | 'REJECT',
    comment?: string
  ): Promise<Remediation> {
    const { data } = await apiClient.post<Remediation>(`/remediations/${remediationId}/review`, {
      decision,
      comment,
    });
    return data;
  },

  async applyRemediation(remediationId: string): Promise<Remediation> {
    const { data } = await apiClient.post<Remediation>(`/remediations/${remediationId}/apply`);
    return data;
  },

  async validateRemediation(
    remediationId: string,
    runTests: boolean = true,
    validationPolicy: string = 'v1.0.0'
  ): Promise<RemediationValidation> {
    const { data } = await apiClient.post<RemediationValidation>(
      `/remediations/${remediationId}/validate`,
      {
        run_tests: runTests,
        validation_policy: validationPolicy,
      }
    );
    return data;
  },

  // ── Validations & Verification ─────────────────────────────

  async getRemediationValidations(remediationId: string): Promise<RemediationValidation[]> {
    const { data } = await apiClient.get<RemediationValidation[]>(
      `/remediations/${remediationId}/validations`
    );
    return data;
  },

  async getValidationDetail(validationId: string): Promise<RemediationValidation> {
    const { data } = await apiClient.get<RemediationValidation>(`/validations/${validationId}`);
    return data;
  },

  async getFindingVerification(findingId: string): Promise<VerificationStatus> {
    const { data } = await apiClient.get<VerificationStatus>(
      `/findings/${findingId}/verification`
    );
    return data;
  },

  // ── Model Registry ─────────────────────────────────────────

  async listModels(runtime?: string, status?: string): Promise<ModelVersion[]> {
    const { data } = await apiClient.get<ModelVersion[]>('/models', {
      params: { runtime, status },
    });
    return data;
  },
};
