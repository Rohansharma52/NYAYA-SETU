import { apiClient } from './client'
import type { DirectoryUser, PaginatedResponse, User } from '../types'

export async function listUsers(params: { skip?: number; limit?: number; role?: string; account_status?: string } = {}): Promise<PaginatedResponse<User>> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== undefined))
  return (await apiClient.get<PaginatedResponse<User>>('/users/', { params: clean })).data
}

export async function officerDirectory(bureauId?: number): Promise<DirectoryUser[]> {
  return (await apiClient.get<DirectoryUser[]>('/users/directory', { params: { bureau_id: bureauId } })).data
}

export async function updateUser(id: number, data: Record<string, unknown>): Promise<User> {
  return (await apiClient.put<User>(`/users/${id}`, data)).data
}

export async function approveUser(id: number) {
  return (await apiClient.post(`/users/${id}/approve`)).data
}

export async function rejectUser(id: number) {
  return (await apiClient.post(`/users/${id}/reject`)).data
}

export async function suspendUser(id: number) {
  return (await apiClient.post(`/users/${id}/suspend`)).data
}

export async function reactivateUser(id: number) {
  return (await apiClient.post(`/users/${id}/reactivate`)).data
}
