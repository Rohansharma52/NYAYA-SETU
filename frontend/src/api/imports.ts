import { apiClient } from './client'

export interface ImportPreviewRow {
  row: number
  data: Record<string, string>
  status: 'valid' | 'error'
  errors: string[]
  warnings: string[]
}

export interface ImportPreviewResult {
  job_id: number
  total_rows: number
  valid_rows: number
  error_rows: number
  preview_rows: ImportPreviewRow[]
  message: string
}

export interface ImportJob {
  id: number
  filename: string
  import_type: string
  status: string
  total_rows: number
  valid_rows: number
  error_rows: number
  imported_rows: number
  created_at?: string
  completed_at?: string
}

export async function previewImport(kind: 'institutions' | 'cases', file: File): Promise<ImportPreviewResult> {
  const form = new FormData()
  form.append('file', file)
  return (await apiClient.post<ImportPreviewResult>(`/imports/${kind}/preview`, form, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}

export async function commitImport(kind: 'institutions' | 'cases', jobId: number) {
  return (await apiClient.post(`/imports/${kind}/commit/${jobId}`)).data
}

export async function listImports(): Promise<ImportJob[]> {
  return (await apiClient.get<ImportJob[]>('/imports/')).data
}
