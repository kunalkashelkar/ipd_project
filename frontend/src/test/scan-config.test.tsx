import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ScanConfig from '../pages/projects/ScanConfig';
import { snapshotService } from '../services/snapshotService';
import { uploadService } from '../services/uploadService';

vi.mock('../services/snapshotService', () => ({
  snapshotService: {
    listSnapshots: vi.fn(),
  },
}));

vi.mock('../services/uploadService', () => ({
  uploadService: {
    listUploads: vi.fn(),
  },
}));

vi.mock('../services/scanService', () => ({
  scanService: {
    createScan: vi.fn(),
  },
}));

describe('ScanConfig UI Consistency Pass — Phase 4-6 Capability Status', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders truthful capability status and descriptions without stale roadmap labels', async () => {
    vi.mocked(snapshotService.listSnapshots).mockResolvedValue({
      items: [
        {
          id: 'snap-1',
          public_id: 'pub-snap-1',
          project_id: 'proj-1',
          repository_id: null,
          repository_commit_id: null,
          source_type: 'upload',
          source_version: 'v1.0',
          commit_sha: 'abc1234567890',
          content_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          artifact_uri: 's3://test/snap-1.zip',
          manifest_uri: null,
          status: 'ready',
          file_count: 5,
          total_bytes: 2048,
          detected_languages: { python: 5 },
          preprocessing_version: 'v1.0.0',
          error_message: null,
          created_by: 'user-1',
          created_at: '2026-09-17T12:00:00Z',
          completed_at: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
    });

    vi.mocked(uploadService.listUploads).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 50,
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-1/scan-config']}>
        <Routes>
          <Route path="/projects/:id/scan-config" element={<ScanConfig />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Configure Analysis Run')).toBeInTheDocument();
    });

    // 1. Verify Status Badges: Native Engine, Active Pipeline, Inference Runtime, Attribution Engine, Sandbox Verification
    expect(screen.getByText('Native Engine')).toBeInTheDocument();
    expect(screen.getByText('Active Pipeline')).toBeInTheDocument();
    expect(screen.getByText('Inference Runtime')).toBeInTheDocument();
    expect(screen.getByText('Attribution Engine')).toBeInTheDocument();
    expect(screen.getByText('Sandbox Verification')).toBeInTheDocument();

    // 2. Verify stale roadmap text is NOT present
    expect(screen.queryByText('Phase 5 Reserved')).not.toBeInTheDocument();
    expect(screen.queryByText('Planned (Phase 6)')).not.toBeInTheDocument();

    // 3. Verify PDG native fallback truthfulness
    expect(
      screen.getByText(/PDG: Unsupported in native fallback; requires Joern engine/i)
    ).toBeInTheDocument();

    // 4. Verify Taint truthfulness (zero taint paths does not guarantee secure code)
    expect(
      screen.getByText(/Zero detected taint paths does not guarantee code is secure/i)
    ).toBeInTheDocument();

    // 5. Verify AI detection boundary truthfulness
    expect(
      screen.getByText(/Inference via configured AI provider \(MockAIProvider \/ LocalTorchProvider boundary\)/i)
    ).toBeInTheDocument();

    // 6. Verify XAI truthfulness
    expect(
      screen.getByText(/Unconfigured runtimes report explicit MODEL_NOT_READY/i)
    ).toBeInTheDocument();

    // 7. Verify Remediation truthfulness (no automatic merging / direct deployment)
    expect(
      screen.getByText(/No automatic merging or direct deployment/i)
    ).toBeInTheDocument();
  });
});
