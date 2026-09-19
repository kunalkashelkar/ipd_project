import { describe, it, expect, vi, beforeEach } from 'vitest';
import { reportService } from '../services/reportService';
import { analyticsService } from '../services/analyticsService';
import { securityGateService } from '../services/securityGateService';
import { findingService } from '../services/findingService';
import apiClient from '../services/api';
import { Report, AnalyticsMetrics, ScanComparisonResult, SecurityGatePolicy, PRSecurityResult } from '../types';

vi.mock('../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
  },
}));

describe('Phase 7: Reports Service Contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches reports with project and scan filters', async () => {
    const mockReportsResponse = {
      items: [
        {
          id: 'rep-1',
          organization_id: 'org-1',
          scan_id: 'scan-1',
          report_type: 'security' as const,
          format: 'pdf' as const,
          status: 'completed' as const,
          file_path: 'reports/rep-1.pdf',
          created_at: '2026-09-18T10:00:00Z',
          files: [
            {
              id: 'file-1',
              report_id: 'rep-1',
              format: 'pdf',
              file_size: 45000,
              created_at: '2026-09-18T10:01:00Z',
            },
          ],
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockReportsResponse });

    const result = await reportService.getReports({ project_id: 'proj-1', scan_id: 'scan-1' });
    expect(apiClient.get).toHaveBeenCalledWith('/reports', {
      params: { project_id: 'proj-1', scan_id: 'scan-1' },
    });
    expect(result.items).toHaveLength(1);
    expect(result.items[0].report_type).toBe('security');
    expect(result.items[0].files).toHaveLength(1);
  });

  it('submits a report generation request', async () => {
    const mockReport: Report = {
      id: 'rep-2',
      public_id: 'rep_pub_2',
      organization_id: 'org-1',
      scan_id: 'scan-1',
      report_type: 'executive',
      format: 'pdf',
      file_path: null,
      status: 'pending',
      created_at: '2026-09-18T10:05:00Z',
      files: [],
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: mockReport });

    const result = await reportService.requestReport({
      scan_id: 'scan-1',
      report_type: 'executive',
      format: 'pdf',
    });

    expect(apiClient.post).toHaveBeenCalledWith('/reports', {
      scan_id: 'scan-1',
      report_type: 'executive',
      format: 'pdf',
    });
    expect(result.status).toBe('pending');
    expect(result.report_type).toBe('executive');
  });

  it('retries a failed report', async () => {
    const retriedReport: Report = {
      id: 'rep-failed-1',
      public_id: 'rep_pub_failed',
      organization_id: 'org-1',
      scan_id: 'scan-1',
      report_type: 'developer',
      format: 'html',
      file_path: null,
      status: 'pending',
      created_at: '2026-09-18T10:10:00Z',
      files: [],
    };

    vi.mocked(apiClient.post).mockResolvedValue({ data: retriedReport });

    const result = await reportService.retryReport('rep-failed-1');
    expect(apiClient.post).toHaveBeenCalledWith('/reports/rep-failed-1/retry');
    expect(result.status).toBe('pending');
  });
});

describe('Phase 7: Analytics Service Contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches organization-wide analytics and health score', async () => {
    const mockAnalytics: AnalyticsMetrics = {
      total_findings: 17,
      active_findings: 7,
      resolved_findings: 10,
      critical_findings: 0,
      severity_breakdown: { critical: 0, high: 2, medium: 5, low: 10 },
      cwe_distribution: [{ cwe_id: 'CWE-89', count: 1 }, { cwe_id: 'CWE-79', count: 4 }],
      risk_trend: [
        { date: '2026-09-15', avg_risk_score: 6.5, active_findings: 12 },
        { date: '2026-09-18', avg_risk_score: 4.2, active_findings: 7 },
      ],
      mttr_hours: 36.0,
      remediation_rate: 85.0,
      false_positive_rate: 4.2,
      health_score: {
        score: 87.5,
        rating: 'B',
        version: 'v1.0.0',
        weights: {
          critical_vulnerabilities: 0.35,
          high_vulnerabilities: 0.25,
        },
      },
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockAnalytics });

    const result = await analyticsService.getOrganizationAnalytics();
    expect(apiClient.get).toHaveBeenCalledWith('/analytics', { params: undefined });
    expect(result.health_score.score).toBe(87.5);
    expect(result.health_score.rating).toBe('B');
    expect(result.health_score.version).toBe('v1.0.0');
    expect(result.remediation_rate).toBe(85.0);
  });

  it('compares two scans for baseline diffing', async () => {
    const mockDiff: ScanComparisonResult = {
      baseline_scan: {
        id: 'scan-base',
        public_id: 'scn_base',
      },
      current_scan: {
        id: 'scan-target',
        public_id: 'scn_target',
      },
      existing_count: 1,
      new_count: 1,
      fixed_count: 1,
      existing_findings: [
        { id: 'f-exist', public_id: 'fnd_exist', fingerprint: 'fp-1', title: 'SQL Injection in auth', severity: 'high' },
      ],
      new_findings: [
        { id: 'f-new', public_id: 'fnd_new', fingerprint: 'fp-2', title: 'Unsanitized input in profile', severity: 'critical' },
      ],
      fixed_findings: [
        { id: 'f-fixed', public_id: 'fnd_fixed', fingerprint: 'fp-3', title: 'Hardcoded test key', severity: 'medium' },
      ],
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockDiff });

    const result = await analyticsService.compareScans('proj-1', 'scan-base', 'scan-target');
    expect(apiClient.get).toHaveBeenCalledWith(
      '/projects/proj-1/analytics/compare?scan_a_id=scan-base&scan_b_id=scan-target&baseline_scan_id=scan-base&current_scan_id=scan-target'
    );
    expect(result.new_count).toBe(1);
    expect(result.fixed_count).toBe(1);
    expect(result.new_findings[0].severity).toBe('critical');
  });
});

describe('Phase 7: Security Gate & PR Gate Service Contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and updates security gate policy', async () => {
    const mockPolicy: SecurityGatePolicy = {
      id: 'gate-pol-1',
      project_id: 'proj-1',
      block_new_critical: true,
      block_new_high: true,
      block_secrets: true,
      cvss_threshold: 7.0,
      version: 'v1.0.0',
      updated_at: '2026-09-18T11:00:00Z',
    };

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPolicy });
    vi.mocked(apiClient.put).mockResolvedValue({
      data: { ...mockPolicy, block_new_high: false },
    });

    const policy = await securityGateService.getGatePolicy('proj-1');
    expect(apiClient.get).toHaveBeenCalledWith('/projects/proj-1/gate-policy');
    expect(policy.block_new_critical).toBe(true);

    const updated = await securityGateService.updateGatePolicy('proj-1', {
      block_new_high: false,
    });
    expect(apiClient.put).toHaveBeenCalledWith('/projects/proj-1/gate-policy', {
      block_new_high: false,
    });
    expect(updated.block_new_high).toBe(false);
  });

  it('lists PR security results for a project', async () => {
    const mockPRResults: PRSecurityResult[] = [
      {
        id: 'pr-sec-1',
        public_id: 'pr_sec_1',
        project_id: 'proj-1',
        repository_id: 'repo-1',
        pull_request_number: 42,
        pr_head_sha: 'abc1234567890',
        pr_scan_id: 'scan-pr-1',
        gate_result: 'FAIL',
        status: 'completed',
        summary: '### Security Gate Failed\n- 1 Critical finding introduced',
        new_count: 1,
        existing_count: 0,
        fixed_count: 2,
        created_at: '2026-09-18T11:15:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockPRResults });

    const results = await securityGateService.getPRSecurityResults('proj-1');
    expect(apiClient.get).toHaveBeenCalledWith('/projects/proj-1/pr-results');
    expect(results).toHaveLength(1);
    expect(results[0].gate_result).toBe('FAIL');
    expect(results[0].pull_request_number).toBe(42);
    expect(results[0].fixed_count).toBe(2);
  });
});

describe('Phase 7: Team Collaboration & Activity Stream Contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('retrieves finding activity timeline', async () => {
    const mockActivity = [
      {
        id: 'act-1',
        actor_name: 'Alice SecOps',
        action: 'COMMENT_ADDED',
        description: 'Mentioned @bob to verify the sanitized query',
        created_at: '2026-09-18T11:30:00Z',
      },
      {
        id: 'act-2',
        actor_name: 'Bob Dev',
        action: 'STATUS_CHANGED',
        description: 'Status changed from OPEN to IN_REMEDIATION',
        created_at: '2026-09-18T11:35:00Z',
      },
    ];

    vi.mocked(apiClient.get).mockResolvedValue({ data: mockActivity });

    const activity = await findingService.getActivity('find-1');
    expect(apiClient.get).toHaveBeenCalledWith('/findings/find-1/activity');
    expect(activity).toHaveLength(2);
    expect(activity[0].action).toBe('COMMENT_ADDED');
    expect(activity[1].actor_name).toBe('Bob Dev');
  });
});
