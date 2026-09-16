// ============================================================
// API Key Service — Phase 2 Organization API Keys
// ============================================================

import apiClient from './api';

export interface ApiKeyMetadata {
  id: string;
  name: string;
  key_prefix: string;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}

export interface ApiKeyCreated {
  id: string;
  name: string;
  key_prefix: string;
  api_key: string; // Plaintext secret returned ONLY ONCE upon creation
  expires_at: string | null;
  created_at: string;
}

export const apiKeyService = {
  async listApiKeys(organizationId: string): Promise<ApiKeyMetadata[]> {
    const { data } = await apiClient.get<ApiKeyMetadata[]>(
      `/organizations/${organizationId}/api-keys`
    );
    return data;
  },

  async createApiKey(
    organizationId: string,
    name: string,
    expiresInDays?: number
  ): Promise<ApiKeyCreated> {
    const { data } = await apiClient.post<ApiKeyCreated>(
      `/organizations/${organizationId}/api-keys`,
      {
        name,
        expires_in_days: expiresInDays || null,
      }
    );
    return data;
  },

  async revokeApiKey(organizationId: string, keyId: string): Promise<void> {
    await apiClient.delete(`/organizations/${organizationId}/api-keys/${keyId}`);
  },
};
