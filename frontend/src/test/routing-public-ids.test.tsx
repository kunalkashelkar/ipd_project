import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import {
  getProjectUrl,
  getSnapshotUrl,
  getScanUrl,
  getScanProgressUrl,
  getScanConfigUrl,
  getResultsUrl,
  toProjectSlug,
  toScanSlug,
  toSnapshotSlug,
  toFindingSlug,
} from '../utils/routes';
import { TopBar } from '../components/TopBar';

vi.mock('../store', () => ({
  useAuthStore: () => ({
    user: { email: 'admin@test.com' },
    activeOrganization: { id: 'org_1', name: 'Test Org' },
    logout: vi.fn(),
  }),
}));

describe('Canonical Public Routing System & Route Builders', () => {
  const sampleProject = {
    id: '6a097cfc-ca21-4828-9a75-6c1f12147fe6',
    public_id: 'prj_4mkft3g6oc5l',
    name: 'hello test2',
  };

  const sampleSnapshot = {
    id: '329d9c0f-744e-4d6a-bf27-2319c0c07af8',
    public_id: 'snp_9k2m1n8b7v6c',
  };

  const sampleScan = {
    id: '81b7e289-e137-4f68-963c-dcbf63297a7e',
    public_id: 'scn_a5eyiy0t4f8r',
    project_id: '6a097cfc-ca21-4828-9a75-6c1f12147fe6',
    project_public_id: 'prj_4mkft3g6oc5l',
  };

  const sampleFinding = {
    id: 'f8ed8c05-d912-40ae-a476-c2cf9df373b5',
    public_id: 'fnd_8Kx3Lm2Q',
  };

  it('resolves project public_id consistently rather than UUID', () => {
    expect(toProjectSlug(sampleProject)).toBe('prj_4mkft3g6oc5l');
    expect(getProjectUrl(sampleProject)).toBe('/projects/prj_4mkft3g6oc5l');
    expect(getProjectUrl(sampleProject)).not.toContain('6a097cfc-ca21-4828-9a75-6c1f12147fe6');
  });

  it('resolves snapshot URL using project.public_id + snapshot.public_id', () => {
    expect(toSnapshotSlug(sampleSnapshot)).toBe('snp_9k2m1n8b7v6c');
    const url = getSnapshotUrl(sampleProject, sampleSnapshot);
    expect(url).toBe('/projects/prj_4mkft3g6oc5l/snapshots/snp_9k2m1n8b7v6c');
    expect(url).not.toContain('6a097cfc-ca21-4828-9a75-6c1f12147fe6');
    expect(url).not.toContain('329d9c0f-744e-4d6a-bf27-2319c0c07af8');
  });

  it('resolves scan execution URLs using canonical public IDs', () => {
    expect(toScanSlug(sampleScan)).toBe('scn_a5eyiy0t4f8r');
    const scanUrl = getScanUrl(sampleProject, sampleScan);
    expect(scanUrl).toBe('/projects/prj_4mkft3g6oc5l/scans/scn_a5eyiy0t4f8r');

    const progressUrl = getScanProgressUrl(sampleProject, sampleScan);
    expect(progressUrl).toBe('/projects/prj_4mkft3g6oc5l/scan-progress/scn_a5eyiy0t4f8r');

    const configUrl = getScanConfigUrl(sampleProject);
    expect(configUrl).toBe('/projects/prj_4mkft3g6oc5l/scan-config');
  });

  it('resolves Results Workspace route using canonical path structure', () => {
    const resultsUrl = getResultsUrl(sampleProject, sampleScan);
    expect(resultsUrl).toBe('/projects/prj_4mkft3g6oc5l/scans/scn_a5eyiy0t4f8r/results');
    expect(resultsUrl).not.toContain('?scan_id=');
    expect(resultsUrl).not.toContain('6a097cfc');
  });

  it('resolves Results Workspace route with finding query param using finding.public_id', () => {
    expect(toFindingSlug(sampleFinding)).toBe('fnd_8Kx3Lm2Q');
    const resultsWithFinding = getResultsUrl(sampleProject, sampleScan, sampleFinding);
    expect(resultsWithFinding).toBe(
      '/projects/prj_4mkft3g6oc5l/scans/scn_a5eyiy0t4f8r/results?finding=fnd_8Kx3Lm2Q'
    );
  });

  it('verifies breadcrumbs prefer human-readable project names instead of raw UUIDs', () => {
    render(
      <MemoryRouter initialEntries={['/projects/prj_4mkft3g6oc5l/scans/scn_a5eyiy0t4f8r/results']}>
        <TopBar />
      </MemoryRouter>
    );

    // Breadcrumbs should display Projects > ... > Results
    expect(screen.getByText(/projects/i)).toBeInTheDocument();
    expect(screen.getByText(/results/i)).toBeInTheDocument();
    // No full UUID should be displayed
    expect(screen.queryByText('6a097cfc-ca21-4828-9a75-6c1f12147fe6')).not.toBeInTheDocument();
  });
});
