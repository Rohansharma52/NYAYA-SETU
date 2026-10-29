import { apiClient } from './client'
import type { Bureau } from '../types'

export async function listBureaus(): Promise<Bureau[]> {
  const res = await apiClient.get<{ items: Bureau[] }>('/bureaus/', { params: { limit: 100 } })
  return res.data.items
}
