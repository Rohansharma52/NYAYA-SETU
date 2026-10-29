import { apiClient } from './client'
import type { CaseRelationship, PaginatedResponse } from '../types'

export async function listRelationships(params: { skip?: number; limit?: number; review_status?: string; relationship_type?: string; case_id?: number; institution_id?: number } = {}): Promise<PaginatedResponse<CaseRelationship>> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== undefined))
  return (await apiClient.get<PaginatedResponse<CaseRelationship>>('/relationships/', { params: clean })).data
}

export async function reviewRelationship(id: number, data: { decision: string; rationale: string; corrected_type?: string }) {
  return (await apiClient.post(`/relationships/${id}/review`, data)).data
}
