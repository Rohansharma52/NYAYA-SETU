import { apiClient } from './client'
import type { CoordinationItem, PaginatedResponse } from '../types'

export async function listCoordination(params: { skip?: number; limit?: number; status?: string } = {}): Promise<PaginatedResponse<CoordinationItem>> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== undefined))
  return (await apiClient.get<PaginatedResponse<CoordinationItem>>('/coordination/', { params: clean })).data
}

export async function getCoordination(id: number): Promise<CoordinationItem> {
  return (await apiClient.get<CoordinationItem>(`/coordination/${id}`)).data
}

export async function createCoordination(data: Record<string, unknown>): Promise<CoordinationItem> {
  return (await apiClient.post<CoordinationItem>('/coordination/', data)).data
}

export async function acknowledge(id: number) {
  return (await apiClient.post(`/coordination/${id}/acknowledge`)).data
}

export async function recordDecision(id: number, data: { decision: string; rationale?: string }) {
  return (await apiClient.post(`/coordination/${id}/decision`, data)).data
}

export async function addTask(id: number, data: { title: string; description?: string; due_date?: string; assigned_to_id?: number }) {
  return (await apiClient.post(`/coordination/${id}/tasks`, data)).data
}

export async function completeTask(coordId: number, taskId: number, data: { completion_notes?: string } = {}) {
  return (await apiClient.put(`/coordination/${coordId}/tasks/${taskId}`, data)).data
}

export async function closeCoordination(id: number, data: { closure_notes: string; is_exception?: boolean; exception_reason?: string }) {
  return (await apiClient.post(`/coordination/${id}/close`, data)).data
}
