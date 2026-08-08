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
    role: string = 'researcher'
  ): Promise<AuthResponse> {
    const { data } = await apiClient.post<AuthResponse>('/auth/register', {
      name,
      email,
      password,
      role,
    });
    return data;
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout');
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
};
