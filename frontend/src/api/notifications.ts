import { apiClient } from './client'
import type { Notification, PaginatedResponse } from '../types'

export async function listNotifications(params: { skip?: number; limit?: number; unread_only?: boolean } = {}): Promise<PaginatedResponse<Notification>> {
  return (await apiClient.get<PaginatedResponse<Notification>>('/notifications/', { params })).data
}

export async function getUnreadCount(): Promise<{ count: number }> {
  const data = (await apiClient.get('/notifications/unread-count')).data as { count?: number; unread_count?: number }
  return { count: data.count ?? data.unread_count ?? 0 }
}

export async function markRead(id: number) {
  return (await apiClient.post(`/notifications/${id}/read`)).data
}

export async function markAllRead() {
  return (await apiClient.post('/notifications/read-all')).data
}
