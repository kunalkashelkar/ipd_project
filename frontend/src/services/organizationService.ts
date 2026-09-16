// ============================================================
// Organization Service — Workspaces & Tenancy
// ============================================================

import apiClient from './api';
import { Organization } from '../types';

export const organizationService = {
  async listOrganizations(): Promise<Organization[]> {
    const response = await apiClient.get<Organization[]>('/organizations');
    return response.data;
  },

  async createOrganization(name: string, description?: string): Promise<Organization> {
    const response = await apiClient.post<Organization>('/organizations', {
      name,
      description,
    });
    return response.data;
  },

  async getOrganization(orgId: string): Promise<Organization> {
    const response = await apiClient.get<Organization>(`/organizations/${orgId}`);
    return response.data;
  },

  async updateOrganization(
    orgId: string,
    data: { name?: string; description?: string }
  ): Promise<Organization> {
    const response = await apiClient.patch<Organization>(`/organizations/${orgId}`, data);
    return response.data;
  },
};
