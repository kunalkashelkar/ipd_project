// ============================================================
// Repository Service — Phase 3 VCS & Git/GitHub Integration
// ============================================================

import apiClient from './api';
import {
  Repository,
  RepositoryBranch,
  RepositoryCommit,
  PaginatedData,
} from '../types';

export const repositoryService = {
  async connectRepository(
    projectId: string,
    data: {
      provider: 'local_git' | 'github';
      repo_url: string;
      display_name?: string;
      access_token?: string;
      default_branch?: string;
    }
  ): Promise<Repository> {
    const { data: repo } = await apiClient.post<Repository>(
      `/projects/${projectId}/repositories`,
      data
    );
    return repo;
  },

  async listRepositories(projectId: string): Promise<Repository[]> {
    const { data } = await apiClient.get<Repository[]>(
      `/projects/${projectId}/repositories`
    );
    return data;
  },

  async getRepository(
    projectId: string,
    repoId: string
  ): Promise<Repository> {
    const { data } = await apiClient.get<Repository>(
      `/projects/${projectId}/repositories/${repoId}`
    );
    return data;
  },

  async listBranches(repoId: string): Promise<RepositoryBranch[]> {
    const { data } = await apiClient.get<RepositoryBranch[]>(
      `/repositories/${repoId}/branches`
    );
    return data;
  },

  async selectBranch(
    repoId: string,
    branchName: string
  ): Promise<Repository> {
    const { data } = await apiClient.post<Repository>(
      `/repositories/${repoId}/branches/select`,
      { branch_name: branchName }
    );
    return data;
  },

  async listCommits(
    repoId: string,
    params?: { page?: number; page_size?: number; branch?: string }
  ): Promise<PaginatedData<RepositoryCommit>> {
    const { data } = await apiClient.get<PaginatedData<RepositoryCommit>>(
      `/repositories/${repoId}/commits`,
      { params }
    );
    return data;
  },

  async syncRepository(
    projectId: string,
    repoId: string
  ): Promise<{ status: string; message: string }> {
    const { data } = await apiClient.post<{ status: string; message: string }>(
      `/projects/${projectId}/repositories/${repoId}/sync`
    );
    return data;
  },

  async disconnectRepository(
    projectId: string,
    repoId: string
  ): Promise<Repository> {
    const { data } = await apiClient.post<Repository>(
      `/projects/${projectId}/repositories/${repoId}/disconnect`
    );
    return data;
  },
};
