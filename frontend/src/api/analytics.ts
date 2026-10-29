import { apiClient } from './client'

export interface Overview {
  totals: { received: number; pending: number; under_process: number; escalated: number; transferred: number; disposed: number }
  pending_beyond_timeline: number
  approaching_timeline: number
  disposal_rate: number
  avg_disposal_days: number | null
  on_time_disposal_rate: number | null
  bureau_workload: { bureau_id: number; code: string; name: string; total: number; open: number; overdue: number; disposed: number; escalated: number; disposal_rate: number }[]
  by_status: Record<string, number>
  institutions: { institution_id: number; name: string; short_name: string | null; region: string | null; total: number; open: number; overdue: number; disposed: number; bureaus: string[] }[]
  ageing: { bucket: string; count: number }[]
  trend: { month: string; received: number; disposed: number }[]
  generated_at: string
}

export async function getOverview(params: { bureau_id?: number; region?: string } = {}): Promise<Overview> {
  return (await apiClient.get<Overview>('/analytics/overview', { params })).data
}

export interface PerformanceRow {
  period: string
  label: string
  received: number
  disposed: number
  disposed_on_time: number
  clearance_rate: number | null
  avg_disposal_days: number | null
  on_time_rate: number | null
  pending_end: number
}

export interface Performance {
  period: 'monthly' | 'quarterly'
  rows: PerformanceRow[]
  by_bureau: { bureau_code: string; bureau_name: string; received: number; disposed: number; on_time: number; clearance_rate: number | null; avg_disposal_days: number | null; on_time_rate: number | null }[]
  summary: { received: number; disposed: number; clearance_rate: number | null }
  definitions: Record<string, string>
}

export async function getPerformance(params: { period: string; months?: number; bureau_id?: number; region?: string }): Promise<Performance> {
  return (await apiClient.get<Performance>('/analytics/performance', { params })).data
}

export interface RegionRow {
  region: string
  total: number
  open: number
  overdue: number
  disposed: number
  institutions: number
  disposal_rate: number
}

export async function getRegions(): Promise<{ items: RegionRow[] }> {
  return (await apiClient.get('/analytics/regions')).data
}

export interface SlaStatus {
  overdue_cases: { case_id: number; case_number: string; days_remaining: number; title: string }[]
  approaching_cases: { case_id: number; case_number: string; days_remaining: number; title: string }[]
  overdue_count: number
  approaching_deadline_count: number
  on_track: number
  no_deadline_set: number
  total_active: number
}

export async function getSlaStatus(): Promise<SlaStatus> {
  return (await apiClient.get<SlaStatus>('/analytics/sla-status')).data
}
