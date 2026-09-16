// ============================================================
// Snapshot Service — Phase 3 Source Ingestion & Preprocessing
// ============================================================

import apiClient from './api';
import {
  SourceSnapshot,
  SourceFile,
  SourceFileContent,
  FunctionModel,
  PaginatedData,
} from '../types';

export const snapshotService = {
  async uploadZip(
    projectId: string,
    file: File,
    onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
  ): Promise<SourceSnapshot> {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await apiClient.post<SourceSnapshot>(
      `/projects/${projectId}/snapshots/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
      }
    );
    return data;
  },

  async uploadFiles(
    projectId: string,
    files: File[],
    paths?: string[],
    onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
  ): Promise<SourceSnapshot> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });
    if (paths && paths.length > 0) {
      paths.forEach((p) => {
        formData.append('paths', p);
      });
    }

    const { data } = await apiClient.post<SourceSnapshot>(
      `/projects/${projectId}/snapshots/files`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress,
      }
    );
    return data;
  },

  async listSnapshots(
    projectId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedData<SourceSnapshot>> {
    const { data } = await apiClient.get<PaginatedData<SourceSnapshot>>(
      `/projects/${projectId}/snapshots`,
      { params }
    );
    return data;
  },

  async getSnapshot(
    projectId: string,
    snapshotId: string
  ): Promise<SourceSnapshot> {
    const { data } = await apiClient.get<SourceSnapshot>(
      `/projects/${projectId}/snapshots/${snapshotId}`
    );
    return data;
  },

  async listFiles(
    projectId: string,
    snapshotId: string,
    params?: {
      page?: number;
      page_size?: number;
      search?: string;
      language?: string;
      classification?: string;
    }
  ): Promise<PaginatedData<SourceFile>> {
    const { data } = await apiClient.get<PaginatedData<SourceFile>>(
      `/projects/${projectId}/snapshots/${snapshotId}/files`,
      { params }
    );
    return data;
  },

  async getFileContent(
    projectId: string,
    snapshotId: string,
    fileId: string
  ): Promise<SourceFileContent> {
    const { data } = await apiClient.get<SourceFileContent>(
      `/projects/${projectId}/snapshots/${snapshotId}/files/${fileId}/content`
    );
    return data;
  },

  async listFunctions(
    projectId: string,
    snapshotId: string,
    params?: {
      page?: number;
      page_size?: number;
      search?: string;
      language?: string;
      file_id?: string;
    }
  ): Promise<PaginatedData<FunctionModel>> {
    const { data } = await apiClient.get<PaginatedData<FunctionModel>>(
      `/projects/${projectId}/snapshots/${snapshotId}/functions`,
      { params }
    );
    return data;
  },
};
