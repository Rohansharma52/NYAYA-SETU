import { apiClient } from './client'
import type { Institution, PaginatedResponse } from '../types'

export interface ListInstitutionsParams {
  skip?: number
  limit?: number
  search?: string
  state?: string
  region?: string
  institution_type?: string
}

export async function listInstitutions(params: ListInstitutionsParams = {}): Promise<PaginatedResponse<Institution>> {
  const { search, ...rest } = params
  const clean = Object.fromEntries(Object.entries({ ...rest, q: search }).filter(([, v]) => v !== '' && v !== undefined))
  return (await apiClient.get<PaginatedResponse<Institution>>('/institutions/', { params: clean })).data
}

export async function getInstitution(id: number): Promise<Institution> {
  return (await apiClient.get<Institution>(`/institutions/${id}`)).data
}
