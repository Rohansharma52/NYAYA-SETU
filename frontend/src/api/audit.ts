import { apiClient } from './client'
import type { PaginatedResponse } from '../types'

export interface AuditEvent {
  id: number
  user_id?: number | null
  user_name?: string | null
  action: string
  resource_type: string
  resource_id?: number | null
  description?: string | null
  created_at: string
}

export async function listAudit(params: { skip?: number; limit?: number; resource_type?: string; action?: string } = {}): Promise<PaginatedResponse<AuditEvent>> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== undefined))
  return (await apiClient.get<PaginatedResponse<AuditEvent>>('/audit/', { params: clean })).data
}
