import { apiClient } from './client'
import type { OverlapCluster, ResolveResult, RiskProfile, InstitutionBrief, CaseBrief, OverlapAnalysis } from '../types'

export interface OverlapSummary {
  institutions: number
  critical: number
  high: number
  medium: number
  low: number
  conflicts: number
  duplicates: number
  awaiting_coordination: number
}

export async function listOverlaps(params: { severity?: string; bureau_id?: number } = {}): Promise<{ summary: OverlapSummary; items: OverlapCluster[]; generated_at: string }> {
  return (await apiClient.get('/intelligence/overlaps', { params })).data
}

export async function startCoordination(institutionId: number, data: { lead_bureau_id?: number; note?: string } = {}) {
  return (await apiClient.post<{ id: number; reference_number: string; lead_bureau: string; message: string }>(
    `/intelligence/overlaps/${institutionId}/coordinate`, data,
  )).data
}

export async function resolveInstitution(data: { text: string; name?: string; email?: string; pincode?: string; aicte_id?: string; top_k?: number }): Promise<ResolveResult> {
  return (await apiClient.post<ResolveResult>('/intelligence/resolve', data)).data
}

export interface BenchmarkMethod {
  label: string
  precision: number
  recall: number
  f1: number
  true_positives: number
  false_positives: number
  by_variant: Record<string, number>
}

export interface BenchmarkResult {
  engine: string
  dataset: { size: number; positives: number; negatives: number; institutions: number; seed: number; variant_labels: Record<string, string> }
  methods: Record<'exact' | 'fuzzy' | 'ire', BenchmarkMethod>
  samples: { variant: string; text: string }[]
  note: string
}

export async function getBenchmark(): Promise<BenchmarkResult> {
  return (await apiClient.get<BenchmarkResult>('/intelligence/benchmark')).data
}

export interface RiskRow {
  institution: InstitutionBrief
  risk: RiskProfile
  case_count: number
  bureaus: string[]
}

export async function getRiskRadar(limit = 50): Promise<{ items: RiskRow[]; levels: Record<string, number> }> {
  return (await apiClient.get('/intelligence/risk', { params: { limit } })).data
}

export interface Institution360 {
  institution: InstitutionBrief & {
    institution_type?: string | null
    district?: string | null
    address?: string | null
    pincode?: string | null
    email?: string | null
    website?: string | null
    phone?: string | null
    status?: string | null
    data_source?: string | null
    identifiers: { id_type: string; id_value: string; is_verified: boolean; source_system?: string | null }[]
    known_aliases: string[]
  }
  cases: CaseBrief[]
  by_bureau: { bureau_code: string; bureau_name: string; total: number; open: number }[]
  overlap: OverlapAnalysis | null
  risk: RiskProfile
  timeline: {
    case_id: number
    case_number: string
    bureau_code: string | null
    action_type: string
    description: string
    performed_by: string | null
    created_at: string | null
  }[]
  coordination: { id: number; reference_number: string; title: string; status: string; lead_bureau_id: number | null }[]
}

export async function getInstitution360(id: number): Promise<Institution360> {
  return (await apiClient.get<Institution360>(`/intelligence/institutions/${id}/360`)).data
}

export interface PulseEvent {
  id: number
  case_id: number
  case_number: string
  bureau_code: string | null
  institution: string | null
  action_type: string
  description: string
  performed_by: string | null
  created_at: string | null
}

export async function getPulse(limit = 15): Promise<{ events: PulseEvent[]; server_time: string }> {
  return (await apiClient.get('/intelligence/pulse', { params: { limit } })).data
}

export async function scanAlerts(): Promise<{ created: Record<string, number>; total: number }> {
  return (await apiClient.post('/intelligence/alerts/scan')).data
}
