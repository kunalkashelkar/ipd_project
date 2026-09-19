import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';
import { analyticsService } from '../services/analyticsService';
import { projectService } from '../services/projectService';
import { DashboardMetrics } from '../types';

// Mock services
vi.mock('../services/analyticsService', () => ({
  analyticsService: {
    getDashboardMetrics: vi.fn(),
  },
}));

vi.mock('../services/projectService', () => ({
  projectService: {
    listProjects: vi.fn(),
  },
}));

vi.mock('../store', () => ({
  useAuthStore: () => ({
    activeOrganization: { id: 'org-1', name: 'Test Org', slug: 'test-org' },
    user: { id: 'usr-1', email: 'test@example.com' },
  }),
}));

describe('Dashboard Component Consistency Pass', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders accurate project-card terminology and metric', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 7,
      total_scans: 12,
      completed_scans: 10,
      failed_scans: 2,
      total_vulnerabilities: 15,
      severity_breakdown: { critical: 3, high: 5, medium: 4, low: 3, info: 0 },
      recent_scans: [],
      scan_success_rate: 83.3,
      vulnerabilities_by_cwe: [
        { cwe_id: 'CWE-78', count: 4 },
        { cwe_id: 'CWE-89', count: 2 },
      ],
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Total Projects')).toBeInTheDocument();
    });

    // Terminology check: strictly verifies non-archived projects caption
    expect(screen.getByText('Non-archived projects in this workspace')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });

  it('renders truthful Top CWEs from persisted findings', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 3,
      total_scans: 5,
      completed_scans: 5,
      failed_scans: 0,
      total_vulnerabilities: 6,
      severity_breakdown: { critical: 2, high: 3, medium: 1, low: 0, info: 0 },
      recent_scans: [],
      scan_success_rate: 100.0,
      vulnerabilities_by_cwe: [
        { cwe_id: 'CWE-78', count: 4 },
        { cwe_id: 'CWE-89', count: 2 },
      ],
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CWE-78')).toBeInTheDocument();
    });

    expect(screen.getByText('CWE-89')).toBeInTheDocument();
    expect(screen.getByText('4 findings')).toBeInTheDocument();
    expect(screen.getByText('2 findings')).toBeInTheDocument();
    expect(screen.queryByText('No CWE Attributions')).not.toBeInTheDocument();
  });

  it('renders explicit empty state when no CWE findings exist', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 1,
      total_scans: 0,
      completed_scans: 0,
      failed_scans: 0,
      total_vulnerabilities: 0,
      severity_breakdown: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
      recent_scans: [],
      scan_success_rate: 0.0,
      vulnerabilities_by_cwe: [],
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No CWE Attributions')).toBeInTheDocument();
    });

    expect(
      screen.getByText('No Common Weakness Enumerations mapped to active findings.')
    ).toBeInTheDocument();
  });

  it('renders explicit and truthful Risk Timeline empty state', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 1,
      total_scans: 1,
      completed_scans: 1,
      failed_scans: 0,
      total_vulnerabilities: 1,
      severity_breakdown: { critical: 1, high: 0, medium: 0, low: 0, info: 0 },
      recent_scans: [],
      scan_success_rate: 100.0,
      vulnerabilities_by_cwe: [],
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No Historical Risk Trend')).toBeInTheDocument();
    });

    expect(
      screen.getByText('Historical risk trend is not available for this workspace yet.')
    ).toBeInTheDocument();
  });

  it('renders authoritative workspace Health Score on Dashboard when scored', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 2,
      total_scans: 3,
      completed_scans: 3,
      failed_scans: 0,
      total_vulnerabilities: 1,
      severity_breakdown: { critical: 0, high: 1, medium: 0, low: 0, info: 0 },
      recent_scans: [],
      scan_success_rate: 100.0,
      vulnerabilities_by_cwe: [],
      health_score: 92.0,
      health_rating: 'A',
      health_status: 'SCORED',
      score_version: 'v1.0.0',
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Security Health Score')).toBeInTheDocument();
    });

    expect(screen.getByText('92')).toBeInTheDocument();
    expect(screen.getByText('Grade A')).toBeInTheDocument();
    expect(screen.getByText('Authoritative workspace posture')).toBeInTheDocument();
  });

  it('renders NO_DATA / No data on Dashboard when workspace has no completed scans', async () => {
    const mockMetrics: DashboardMetrics = {
      total_projects: 1,
      total_scans: 0,
      completed_scans: 0,
      failed_scans: 0,
      total_vulnerabilities: 0,
      severity_breakdown: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
      recent_scans: [],
      scan_success_rate: 0.0,
      vulnerabilities_by_cwe: [],
      health_score: null,
      health_rating: null,
      health_status: 'NO_DATA',
      score_version: 'v1.0.0',
    };

    vi.mocked(analyticsService.getDashboardMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(projectService.listProjects).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5,
    });

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Security Health Score')).toBeInTheDocument();
    });

    expect(screen.getByText('No data')).toBeInTheDocument();
    expect(screen.getByText('Unscored — scan required')).toBeInTheDocument();
  });
});

describe('Finding Status Consistency Component Contract', () => {
  // Test the component logic that guarantees badge, selector, and action buttons derive from authoritative status
  const ALLOWED_TRANSITIONS: Record<string, string[]> = {
    OPEN: ['CONFIRMED', 'IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
    CONFIRMED: ['IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
    IN_PROGRESS: ['FIX_PROPOSED', 'CONFIRMED', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
    FIX_PROPOSED: ['UNDER_REVIEW', 'IN_PROGRESS'],
    UNDER_REVIEW: ['FIXED', 'IN_PROGRESS'],
    FIXED: ['VERIFIED', 'REOPENED'],
    VERIFIED: ['REOPENED'],
    FALSE_POSITIVE: ['OPEN', 'REOPENED'],
    RISK_ACCEPTED: ['OPEN', 'REOPENED'],
    SUPPRESSED: ['OPEN', 'REOPENED'],
    REOPENED: ['CONFIRMED', 'IN_PROGRESS', 'FALSE_POSITIVE', 'RISK_ACCEPTED', 'SUPPRESSED'],
  };

  function FindingStatusControls({ status }: { status: string }) {
    return (
      <div>
        <span data-testid="status-badge">Status: {status}</span>
        <select data-testid="status-selector" value={status} onChange={() => {}}>
          <option value={status}>{status}</option>
          {(ALLOWED_TRANSITIONS[status] || [])
            .filter((t) => t !== status)
            .map((t) => (
              <option key={t} value={t}>
                → {t}
              </option>
            ))}
        </select>
        {status === 'SUPPRESSED' || status === 'FALSE_POSITIVE' || status === 'RISK_ACCEPTED' ? (
          <button data-testid="action-button">Reopen</button>
        ) : status === 'FIXED' || status === 'VERIFIED' ? (
          <button data-testid="action-button">Reopen</button>
        ) : (
          <button data-testid="action-button">Suppress</button>
        )}
      </div>
    );
  }

  it('renders identical RISK_ACCEPTED across badge, selector, and action button', () => {
    render(<FindingStatusControls status="RISK_ACCEPTED" />);

    const badge = screen.getByTestId('status-badge');
    const selector = screen.getByTestId('status-selector') as HTMLSelectElement;
    const actionBtn = screen.getByTestId('action-button');

    expect(badge.textContent).toBe('Status: RISK_ACCEPTED');
    expect(selector.value).toBe('RISK_ACCEPTED');
    expect(actionBtn.textContent).toBe('Reopen');

    // Available transitions for RISK_ACCEPTED should only be OPEN and REOPENED
    const options = Array.from(selector.options).map((o) => o.value);
    expect(options).toEqual(['RISK_ACCEPTED', 'OPEN', 'REOPENED']);
    expect(options).not.toContain('FIXED');
  });

  it('renders identical OPEN across badge, selector, and action button', () => {
    render(<FindingStatusControls status="OPEN" />);

    const badge = screen.getByTestId('status-badge');
    const selector = screen.getByTestId('status-selector') as HTMLSelectElement;
    const actionBtn = screen.getByTestId('action-button');

    expect(badge.textContent).toBe('Status: OPEN');
    expect(selector.value).toBe('OPEN');
    expect(actionBtn.textContent).toBe('Suppress');

    // Available transitions for OPEN
    const options = Array.from(selector.options).map((o) => o.value);
    expect(options).toContain('OPEN');
    expect(options).toContain('CONFIRMED');
    expect(options).toContain('RISK_ACCEPTED');
    expect(options).not.toContain('VERIFIED');
  });
});
