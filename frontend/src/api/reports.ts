import axios from 'axios'
import { apiClient } from './client'
import { downloadBlob } from '../lib/format'

export interface ExportParams {
  status?: string
  bureau_id?: number
  institution_id?: number
  region?: string
  category?: string
  priority?: string
  overdue?: boolean
}

export async function exportCasesCSV(params: ExportParams = {}): Promise<Blob> {
  return (await apiClient.get('/reports/cases/csv', { params, responseType: 'blob' })).data
}

export async function exportCoordinationCSV(): Promise<Blob> {
  return (await apiClient.get('/reports/coordination/csv', { responseType: 'blob' })).data
}

export async function exportCasesPDF(params: ExportParams = {}): Promise<Blob> {
  return (await apiClient.get('/reports/cases/pdf', { params, responseType: 'blob' })).data
}

export async function exportInstitutionPDF(institutionId: number): Promise<Blob> {
  return (await apiClient.get(`/reports/institution/${institutionId}/pdf`, { responseType: 'blob' })).data
}

/** Download a server-generated export, using the file name the server suggests. */
export async function saveExport(path: string, params: Record<string, unknown> = {}, fallbackName = 'nyaya-setu-export'): Promise<string> {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== undefined && v !== null))
  const res = await apiClient.get(path, { params: clean, responseType: 'blob' })
  const cd = String(res.headers['content-disposition'] ?? '')
  const name = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)?.[1] ?? fallbackName
  downloadBlob(res.data as Blob, decodeURIComponent(name))
  return name
}

/** Error responses of blob requests arrive as Blob — read the JSON detail out of them. */
export async function exportErrorMessage(err: unknown): Promise<string> {
  if (axios.isAxiosError(err)) {
    if (!err.response) return 'Cannot reach the NYAYA SETU API server'
    const data = err.response.data
    if (data instanceof Blob) {
      try {
        const j = JSON.parse(await data.text())
        if (typeof j.detail === 'string') return j.detail
      } catch { /* not JSON */ }
    }
    return `Export failed (HTTP ${err.response.status})`
  }
  return 'Export failed'
}
