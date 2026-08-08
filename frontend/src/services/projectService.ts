// ============================================================
// Project Service — CRUD Operations
// ============================================================

import apiClient from './api';
import { Project, PaginatedData } from '../types';

export const projectService = {
  async createProject(data: {
    name: string;
    description?: string;
    language?: string;
    default_branch?: string;
  }): Promise<Project> {
    const { data: project } = await apiClient.post<Project>('/projects', data);
    return project;
  },

  async listProjects(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<PaginatedData<Project>> {
    const { data } = await apiClient.get<PaginatedData<Project>>('/projects', {
      params,
    });
    return data;
  },

  async getProject(projectId: string): Promise<Project> {
    const { data } = await apiClient.get<Project>(`/projects/${projectId}`);
    return data;
  },

  async updateProject(
    projectId: string,
    data: {
      name?: string;
      description?: string;
      language?: string;
      default_branch?: string;
      is_archived?: boolean;
    }
  ): Promise<Project> {
    const { data: project } = await apiClient.put<Project>(
      `/projects/${projectId}`,
      data
    );
    return project;
  },

  async deleteProject(projectId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}`);
  },
};
