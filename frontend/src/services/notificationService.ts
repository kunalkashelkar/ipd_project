// ============================================================
// Notification Service — User Notifications
// ============================================================

import apiClient from './api';
import { Notification, PaginatedData } from '../types';

export const notificationService = {
  async getNotifications(params?: {
    page?: number;
    page_size?: number;
    unread_only?: boolean;
  }): Promise<PaginatedData<Notification>> {
    const { data } = await apiClient.get<PaginatedData<Notification>>(
      '/notifications',
      { params }
    );
    return data;
  },

  async getUnreadCount(): Promise<{ count: number }> {
    const { data } = await apiClient.get<{ count: number }>(
      '/notifications/unread-count'
    );
    return data;
  },

  async markAsRead(notificationId: string): Promise<Notification> {
    const { data } = await apiClient.put<Notification>(
      `/notifications/${notificationId}/read`
    );
    return data;
  },

  async markAllAsRead(): Promise<{ updated_count: number }> {
    const { data } = await apiClient.put<{ updated_count: number }>(
      '/notifications/read-all'
    );
    return data;
  },
};
