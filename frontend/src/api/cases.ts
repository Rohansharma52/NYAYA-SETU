import { apiClient } from './client'
import type { Case, CaseAction, PaginatedResponse } from '../types'

export interface ListCasesParams {
  skip?: number
  limit?: number
  status?: string
  statuses?: string
  bureau_id?: number
  institution_id?: number
  priority?: string
  category?: string
  region?: string
  aicte_id?: string
  overdue?: boolean
  search?: string
  date_from?: string
  date_to?: string
  ageing_bracket?: string
}

export async function listCases(params: ListCasesParams = {}): Promise<PaginatedResponse<Case>> {
  const { search, ...rest } = params
  const clean = Object.fromEntries(Object.entries({ ...rest, q: search }).filter(([, v]) => v !== '' && v !== undefined && v !== null))
  const res = await apiClient.get<PaginatedResponse<Case>>('/cases/', { params: clean })
  return res.data
}

export async function getCase(id: number): Promise<Case> {
  return (await apiClient.get<Case>(`/cases/${id}`)).data
}

export async function createCase(data: Record<string, unknown>): Promise<Case> {
  return (await apiClient.post<Case>('/cases/', data)).data
}

export async function updateCase(id: number, data: Record<string, unknown>): Promise<Case> {
  return (await apiClient.put<Case>(`/cases/${id}`, data)).data
}

export async function changeStatus(id: number, data: { new_status: string; reason: string }) {
  return (await apiClient.post(`/cases/${id}/status`, data)).data
}

export async function assignCase(id: number, data: { officer_id: number; notes?: string }) {
  return (await apiClient.post(`/cases/${id}/assign`, data)).data
}

export async function addAction(id: number, data: { action_type: string; description: string }) {
  return (await apiClient.post(`/cases/${id}/actions`, data)).data
}

export async function getTimeline(id: number): Promise<CaseAction[]> {
  return (await apiClient.get<CaseAction[]>(`/cases/${id}/timeline`)).data
}

export async function requestTransfer(id: number, data: { to_bureau_id: number; reason: string }) {
  return (await apiClient.post(`/cases/${id}/transfer`, data)).data
}

export interface TransferRecord {
  id: number
  case_id: number
  case_number: string | null
  case_title: string | null
  from_bureau: string | null
  to_bureau: string | null
  to_bureau_id: number | null
  reason: string
  status: string
  response_notes: string | null
  requested_by: string | null
  responded_by: string | null
  requested_at: string | null
  responded_at: string | null
}

export async function caseTransfers(id: number): Promise<TransferRecord[]> {
  return (await apiClient.get<TransferRecord[]>(`/cases/${id}/transfers`)).data
}

export async function listTransfers(status = 'requested'): Promise<{ items: TransferRecord[]; total: number }> {
  return (await apiClient.get('/transfers/', { params: { status: status || undefined } })).data
}

export async function respondTransfer(id: number, data: { accept: boolean; notes?: string }) {
  return (await apiClient.post(`/transfers/${id}/respond`, data)).data
}

export interface Attachment {
  id: number
  case_id: number
  filename: string
  content_type: string | null
  size_bytes: number
  sha256: string
  remarks: string | null
  uploaded_by: string | null
  created_at: string | null
}

export async function listAttachments(id: number): Promise<Attachment[]> {
  return (await apiClient.get<Attachment[]>(`/cases/${id}/attachments`)).data
}

export async function uploadAttachment(id: number, file: File, remarks?: string): Promise<Attachment> {
  const fd = new FormData()
  fd.append('file', file)
  if (remarks) fd.append('remarks', remarks)
  return (await apiClient.post<Attachment>(`/cases/${id}/attachments`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}

export async function downloadAttachment(caseId: number, att: Attachment): Promise<Blob> {
  return (await apiClient.get(`/cases/${caseId}/attachments/${att.id}/download`, { responseType: 'blob' })).data
}

export interface ExtensionRequest {
  id: number
  case_id: number
  original_due_date?: string
  requested_due_date: string
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  review_notes?: string
  created_at?: string
}

export async function requestExtension(caseId: number, data: { requested_due_date: string; reason: string }) {
  return (await apiClient.post<ExtensionRequest>(`/cases/${caseId}/extension-requests`, data)).data
}

export async function listExtensions(caseId: number): Promise<ExtensionRequest[]> {
  return (await apiClient.get<ExtensionRequest[]>(`/cases/${caseId}/extension-requests`)).data
}

export async function reviewExtension(caseId: number, extId: number, data: { approved: boolean; review_notes?: string }) {
  return (await apiClient.post(`/cases/${caseId}/extension-requests/${extId}/review`, data)).data
}
