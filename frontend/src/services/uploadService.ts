// ============================================================
// Upload Service — File Uploads & Management
// ============================================================

import apiClient from './api';
import { Upload, PaginatedData } from '../types';

export const uploadService = {
  async uploadFile(
    projectId: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<Upload> {
    const form = new FormData();
    form.append('project_id', projectId);
    form.append('file', file);

    const { data } = await apiClient.post<Upload>('/uploads', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(percent);
        }
      },
    });
    return data;
  },

  async listUploads(
    projectId: string,
    params?: { page?: number; page_size?: number }
  ): Promise<PaginatedData<Upload>> {
    const { data } = await apiClient.get<PaginatedData<Upload>>('/uploads', {
      params: { project_id: projectId, ...params },
    });
    return data;
  },

  async getUpload(uploadId: string): Promise<Upload> {
    const { data } = await apiClient.get<Upload>(`/uploads/${uploadId}`);
    return data;
  },

  async deleteUpload(uploadId: string): Promise<void> {
    await apiClient.delete(`/uploads/${uploadId}`);
  },
};
