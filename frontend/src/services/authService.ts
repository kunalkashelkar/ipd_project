// ============================================================
// Auth Service — Login, Register, Token Management
// ============================================================

import apiClient from './api';
import { AuthResponse, User } from '../types';

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/login', {
      email,
      password,
    });
    return data;
  },

  async register(
    name: string,
    email: string,
    password: string,
    organizationName?: string,
    invitationToken?: string
  ): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/register', {
      name,
      email,
      password,
      organization_name: organizationName || undefined,
      invitation_token: invitationToken || undefined,
    });
    return data;
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Best-effort logout revocation
    }
  },

  async refreshToken(refreshToken: string): Promise<{ tokens: { access_token: string; refresh_token: string } }> {
    const { data } = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return data;
  },

  async getMe(): Promise<User> {
    const { data } = await apiClient.get<User>('/auth/me');
    return data;
  },

  async verifyEmail(token: string): Promise<void> {
    await apiClient.post('/auth/verify-email', { token });
  },

  async requestPasswordReset(email: string): Promise<{ message: string; dev_token?: string; reset_url?: string }> {
    const { data } = await apiClient.post<{ message: string; dev_token?: string; reset_url?: string }>(
      '/auth/request-password-reset',
      { email }
    );
    return data;
  },

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    await apiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },
};
