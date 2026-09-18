import { describe, it, expect, vi, beforeEach } from 'vitest';
import { remediationService } from '../services/remediationService';
import apiClient from '../services/api';
import { Remediation, RemediationValidation, AIExplanation } from '../types/remediation';

vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('Phase 6: Remediation & XAI Frontend Service Contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lists remediations for a finding', async () => {
    const mockRemediations: Remediation[] = [
      {
        id: 'rem-1',
        finding_id: 'find-1',
        organization_id: 'org-1',
        project_id: 'proj-1',
        source_snapshot_id: 'snap-1',
        remediation_number: 1,
        status: 'PROPOSED',
        provider: 'development_provider',
        model_name: 'DeterministicRemediationEngine',
        model_version: 'v1.0.0',
        prompt_version: 'v1.0.0',
        summary: 'Parameterized query fix',
        explanation: 'Replaces string concatenation with parameterized query.',
        diff_content: '--- a/views.py\n+++ b/views.py\n@@ -42,4 +42,4 @@\n-cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n+cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))',
        patch_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        changed_files: ['views.py'],
        warnings: [],
        generated_by_ai: true,
        is_active_candidate: true,
        validations: [],
        created_at: '2026-09-17T12:00:00Z',
        updated_at: '2026-09-17T12:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockRemediations });

    const result = await remediationService.getFindingRemediations('find-1');
    expect(apiClient.get).toHaveBeenCalledWith('/findings/find-1/remediations');
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe('PROPOSED');
    expect(result[0].summary).toBe('Parameterized query fix');
  });

  it('generates a new remediation proposal', async () => {
    const mockRem: Remediation = {
      id: 'rem-2',
      finding_id: 'find-1',
      organization_id: 'org-1',
      project_id: 'proj-1',
      source_snapshot_id: 'snap-1',
      remediation_number: 2,
      status: 'PROPOSED',
      provider: 'development_provider',
      model_name: 'DeterministicRemediationEngine',
      model_version: 'v1.0.0',
      prompt_version: 'v1.0.0',
      summary: 'Input validation fix',
      explanation: 'Adds validation prior to processing.',
      diff_content: '--- a/views.py\n+++ b/views.py\n',
      patch_checksum: 'abc1234567890abcdef',
      changed_files: ['views.py'],
      warnings: [],
      generated_by_ai: true,
      is_active_candidate: true,
      validations: [],
      created_at: '2026-09-17T12:05:00Z',
      updated_at: '2026-09-17T12:05:00Z',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockRem });

    const result = await remediationService.generateFindingRemediation('find-1');
    expect(apiClient.post).toHaveBeenCalledWith('/findings/find-1/remediations', {
      prompt_version: 'v1.0.0',
    });
    expect(result.id).toBe('rem-2');
    expect(result.remediation_number).toBe(2);
  });

  it('reviews remediation (approve/reject)', async () => {
    const approvedRem: Remediation = {
      id: 'rem-1',
      finding_id: 'find-1',
      organization_id: 'org-1',
      project_id: 'proj-1',
      source_snapshot_id: 'snap-1',
      remediation_number: 1,
      status: 'APPROVED',
      provider: 'development_provider',
      model_name: 'DeterministicRemediationEngine',
      model_version: 'v1.0.0',
      prompt_version: 'v1.0.0',
      summary: 'Parameterized query fix',
      explanation: 'Replaces string concatenation.',
      diff_content: '--- a/views.py\n+++ b/views.py',
      patch_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      changed_files: ['views.py'],
      warnings: [],
      generated_by_ai: true,
      is_active_candidate: true,
      validations: [],
      created_at: '2026-09-17T12:00:00Z',
      updated_at: '2026-09-17T12:10:00Z',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: approvedRem });

    const result = await remediationService.reviewRemediation('rem-1', 'APPROVE', 'LGTM');
    expect(apiClient.post).toHaveBeenCalledWith('/remediations/rem-1/review', {
      decision: 'APPROVE',
      comment: 'LGTM',
    });
    expect(result.status).toBe('APPROVED');
  });

  it('validates remediation and receives structured validation report', async () => {
    const mockVal: RemediationValidation = {
      id: 'val-1',
      remediation_id: 'rem-1',
      finding_id: 'find-1',
      source_snapshot_id: 'snap-1',
      organization_id: 'org-1',
      project_id: 'proj-1',
      attempt_number: 1,
      workspace_identifier: '/tmp/test-ws',
      validation_policy_version: 'v1.0.0',
      timeout_seconds: 120,
      status: 'PASSED',
      patch_apply_result: { status: 'PASS', message: 'Applied cleanly' },
      syntax_result: { status: 'PASS', message: 'Syntax valid' },
      build_result: { status: 'SKIPPED', message: 'No build step' },
      test_result: { status: 'SKIPPED', message: 'Tests disabled' },
      static_analysis_result: { status: 'PASS', issue_still_present: false },
      taint_result: { status: 'PASS', message: 'No sinks' },
      graph_result: { status: 'PASS', message: 'Valid' },
      regression_result: { status: 'PASS', regressions_detected: false },
      verification_scan_id: 'scan-verify-1',
      final_verification_result: 'VERIFIED',
      failure_reason: null,
      started_at: '2026-09-17T12:15:00Z',
      completed_at: '2026-09-17T12:15:05Z',
      created_at: '2026-09-17T12:15:00Z',
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockVal });

    const result = await remediationService.validateRemediation('rem-1', false);
    expect(apiClient.post).toHaveBeenCalledWith('/remediations/rem-1/validate', {
      run_tests: false,
      validation_policy: 'v1.0.0',
    });
    expect(result.status).toBe('PASSED');
    expect(result.final_verification_result).toBe('VERIFIED');
    expect(result.verification_scan_id).toBe('scan-verify-1');
  });

  it('fetches authoritative verification status for finding', async () => {
    const mockVerificationStatus = {
      finding_id: 'find-1',
      finding_status: 'VERIFIED',
      is_verified: true,
      verification_scan_id: 'scan-verify-1',
      remediation_id: 'rem-1',
      validation_id: 'val-1',
      remediation_status: 'VALIDATED',
      evidence_summary: {
        original_cwe: 'CWE-89',
        verified_at: '2026-09-17T12:15:05Z',
      },
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockVerificationStatus });

    const result = await remediationService.getFindingVerification('find-1');
    expect(apiClient.get).toHaveBeenCalledWith('/findings/find-1/verification');
    expect(result.is_verified).toBe(true);
    expect(result.finding_status).toBe('VERIFIED');
  });

  it('lists XAI explanations and handles unsupported/unavailable states without fake data', async () => {
    const mockExplanations: AIExplanation[] = [
      {
        id: 'exp-ig-1',
        finding_id: 'find-1',
        source_snapshot_id: 'snap-1',
        organization_id: 'org-1',
        project_id: 'proj-1',
        explanation_method: 'integrated_gradients',
        schema_version: 'v1.0.0',
        method_status: 'MODEL_NOT_READY',
        status_reason: 'PyTorch model checkpoint not configured or missing weights',
        summary: 'Attribution computation unavailable',
        root_cause: 'Model weights are required for Integrated Gradients.',
        why_vulnerable: 'N/A',
        impact: 'N/A',
        evidence_explanation: 'Captum Integrated Gradients requires active torch model.',
        warnings: ['Real model weights not configured'],
        provider: 'local_torch',
        model_name: 'LocalTorchProvider',
        model_version: 'v1.0.0',
        generated_by_ai: true,
        important_locations: [],
        important_tokens: [],
        important_functions: [],
        important_nodes: [],
        important_edges: [],
        created_at: '2026-09-17T12:00:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockExplanations });

    const result = await remediationService.getFindingExplanations('find-1');
    expect(apiClient.get).toHaveBeenCalledWith('/findings/find-1/explanation', { params: undefined });
    expect(result).toHaveLength(1);
    expect(result[0].method_status).toBe('MODEL_NOT_READY');
    expect(result[0].important_locations).toHaveLength(0);
    expect(result[0].status_reason).toContain('checkpoint not configured');
  });
});
