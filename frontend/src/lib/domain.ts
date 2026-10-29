/** Shared domain vocabulary: bureau identity, case status, severity. */

export interface BureauStyle {
  code: string
  name: string
  color: string
  soft: string
  text: string
  ring: string
}

export const BUREAU_STYLES: Record<string, BureauStyle> = {
  RB: { code: 'RB', name: 'Regulation Bureau', color: '#4447DE', soft: 'bg-royal-50', text: 'text-royal-700', ring: 'border-royal-200' },
  PGRC: { code: 'PGRC', name: 'Public Grievance Redressal Cell', color: '#D07206', soft: 'bg-gold-50', text: 'text-gold-700', ring: 'border-gold-200' },
  AB: { code: 'AB', name: 'Approval Bureau', color: '#0E9F8E', soft: 'bg-teal-50', text: 'text-teal-700', ring: 'border-teal-200' },
  ACAD: { code: 'ACAD', name: 'Academic Bureau', color: '#8B5CF6', soft: 'bg-violet-50', text: 'text-violet-700', ring: 'border-violet-200' },
  FIN: { code: 'FIN', name: 'Finance & Scholarship Cell', color: '#DB2777', soft: 'bg-pink-50', text: 'text-pink-700', ring: 'border-pink-200' },
}

const FALLBACK: BureauStyle = { code: '—', name: 'Unassigned', color: '#64748B', soft: 'bg-slate-50', text: 'text-slate-600', ring: 'border-slate-200' }

export function bureauStyle(code?: string | null): BureauStyle {
  if (!code) return FALLBACK
  return BUREAU_STYLES[code] ?? { ...FALLBACK, code }
}

export type StatusGroup = 'pending' | 'under_process' | 'escalated' | 'transferred' | 'disposed'

export const STATUS_META: Record<string, { label: string; group: StatusGroup; dot: string; chip: string }> = {
  received: { label: 'Received', group: 'pending', dot: 'bg-slate-400', chip: 'bg-slate-50 text-slate-700 border-slate-200' },
  triaged: { label: 'Triaged', group: 'pending', dot: 'bg-sky-500', chip: 'bg-sky-50 text-sky-700 border-sky-200' },
  assigned: { label: 'Assigned', group: 'pending', dot: 'bg-royal-500', chip: 'bg-royal-50 text-royal-700 border-royal-200' },
  under_process: { label: 'Under process', group: 'under_process', dot: 'bg-indigo-500', chip: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  awaiting_information: { label: 'Awaiting info', group: 'pending', dot: 'bg-amber-500', chip: 'bg-amber-50 text-amber-700 border-amber-200' },
  decision_review: { label: 'Decision review', group: 'under_process', dot: 'bg-violet-500', chip: 'bg-violet-50 text-violet-700 border-violet-200' },
  disposed: { label: 'Disposed', group: 'disposed', dot: 'bg-emerald-500', chip: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  closed: { label: 'Closed', group: 'disposed', dot: 'bg-emerald-600', chip: 'bg-emerald-50 text-emerald-800 border-emerald-200' },
  escalated: { label: 'Escalated', group: 'escalated', dot: 'bg-rose-500', chip: 'bg-rose-50 text-rose-700 border-rose-200' },
  transfer_requested: { label: 'Transfer requested', group: 'transferred', dot: 'bg-cyan-500', chip: 'bg-cyan-50 text-cyan-700 border-cyan-200' },
  transferred: { label: 'Transferred', group: 'transferred', dot: 'bg-cyan-600', chip: 'bg-cyan-50 text-cyan-800 border-cyan-200' },
  reopened: { label: 'Reopened', group: 'pending', dot: 'bg-orange-500', chip: 'bg-orange-50 text-orange-700 border-orange-200' },
}

export const STATUS_OPTIONS = Object.entries(STATUS_META).map(([value, m]) => ({ value, label: m.label }))

export const OPEN_STATUSES = Object.keys(STATUS_META).filter((s) => !['disposed', 'closed', 'transferred'].includes(s))

export const VALID_TRANSITIONS: Record<string, string[]> = {
  received: ['triaged', 'escalated'],
  triaged: ['assigned', 'escalated'],
  assigned: ['under_process', 'transfer_requested', 'escalated'],
  under_process: ['awaiting_information', 'decision_review', 'disposed', 'transfer_requested', 'escalated'],
  awaiting_information: ['under_process', 'escalated'],
  decision_review: ['disposed', 'under_process'],
  disposed: ['reopened'],
  transfer_requested: ['transferred', 'assigned'],
  transferred: ['assigned'],
  escalated: ['assigned', 'under_process'],
  reopened: ['triaged'],
  closed: ['reopened'],
}

export const SEVERITY_META: Record<string, { label: string; chip: string; dot: string; bar: string; glow: string }> = {
  critical: { label: 'Critical', chip: 'bg-rose-50 text-rose-700 border-rose-200', dot: 'bg-rose-500', bar: 'from-rose-500 to-rose-400', glow: 'shadow-[0_0_0_4px_rgba(244,63,94,.12)]' },
  high: { label: 'High', chip: 'bg-orange-50 text-orange-700 border-orange-200', dot: 'bg-orange-500', bar: 'from-orange-500 to-amber-400', glow: 'shadow-[0_0_0_4px_rgba(249,115,22,.12)]' },
  medium: { label: 'Medium', chip: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-400', bar: 'from-amber-400 to-yellow-300', glow: '' },
  low: { label: 'Informational', chip: 'bg-slate-50 text-slate-600 border-slate-200', dot: 'bg-slate-400', bar: 'from-slate-400 to-slate-300', glow: '' },
  none: { label: 'None', chip: 'bg-slate-50 text-slate-500 border-slate-200', dot: 'bg-slate-300', bar: 'from-slate-300 to-slate-200', glow: '' },
}

export const CLASSIFICATION_META: Record<string, { label: string; chip: string; description: string }> = {
  action_conflict: { label: 'Action conflict', chip: 'bg-rose-50 text-rose-700 border-rose-200', description: 'Bureaus are acting in contradictory or parallel ways' },
  duplicate: { label: 'Duplicate', chip: 'bg-violet-50 text-violet-700 border-violet-200', description: 'Same complaint received through two channels' },
  related_pattern: { label: 'Related issue', chip: 'bg-amber-50 text-amber-700 border-amber-200', description: 'Same issue raised through different channels' },
  independent: { label: 'Independent', chip: 'bg-slate-50 text-slate-600 border-slate-200', description: 'Different issues at the same institution' },
}

export const RISK_META: Record<string, { label: string; color: string; chip: string }> = {
  critical: { label: 'Critical', color: '#E11D48', chip: 'bg-rose-50 text-rose-700 border-rose-200' },
  high: { label: 'High', color: '#EA580C', chip: 'bg-orange-50 text-orange-700 border-orange-200' },
  elevated: { label: 'Elevated', color: '#D97706', chip: 'bg-amber-50 text-amber-700 border-amber-200' },
  low: { label: 'Low', color: '#059669', chip: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
}

export const CATEGORIES = [
  'Fee Refund', 'Fee Regulation', 'Infrastructure', 'Faculty', 'Examination', 'Certificates',
  'Student Welfare', 'Scholarship', 'Admission', 'Placement',
]

export const ROLE_LABELS: Record<string, string> = {
  system_admin: 'System Administrator',
  senior_management: 'Senior Management',
  bureau_officer: 'Bureau Officer',
  regional_officer: 'Regional Officer',
  data_admin: 'Data Administrator',
  coordination_reviewer: 'Coordination Reviewer',
}

export const REGIONS = ['Northern', 'North-West', 'Central', 'Eastern', 'Western', 'Southern', 'South-West', 'South-Central']
