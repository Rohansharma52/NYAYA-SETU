// ─── Enums ────────────────────────────────────────────────────────────────────

export enum UserRole {
  system_admin = 'system_admin',
  senior_management = 'senior_management',
  bureau_officer = 'bureau_officer',
  regional_officer = 'regional_officer',
  data_admin = 'data_admin',
  coordination_reviewer = 'coordination_reviewer',
}

export enum CaseStatus {
  received = 'received',
  triaged = 'triaged',
  assigned = 'assigned',
  under_process = 'under_process',
  awaiting_information = 'awaiting_information',
  decision_review = 'decision_review',
  disposed = 'disposed',
  escalated = 'escalated',
  transfer_requested = 'transfer_requested',
  transferred = 'transferred',
  reopened = 'reopened',
  closed = 'closed',
}

export enum CasePriority {
  low = 'low',
  medium = 'medium',
  high = 'high',
  urgent = 'urgent',
}

// ─── Core models ──────────────────────────────────────────────────────────────

export interface Bureau {
  id: number
  code: string
  name: string
  description?: string
  head_name?: string
  is_active: boolean
}

export interface User {
  id: number
  email: string
  full_name: string
  role: UserRole | string
  account_status: string
  bureau_id?: number | null
  region?: string | null
  designation?: string | null
  is_active: boolean
  last_login?: string | null
  created_at?: string
}

export interface DirectoryUser {
  id: number
  full_name: string
  designation?: string | null
  bureau_id?: number | null
  role: string
}

export interface InstitutionIdentifier {
  id: number
  id_type: string
  id_value: string
  source_system?: string | null
  is_primary: boolean
  is_verified: boolean
}

export interface Institution {
  id: number
  canonical_name: string
  short_name?: string | null
  institution_type?: string | null
  status: string
  state?: string | null
  district?: string | null
  city?: string | null
  region?: string | null
  address?: string | null
  pincode?: string | null
  email?: string | null
  website?: string | null
  identifiers: InstitutionIdentifier[]
  total_cases?: number
  open_cases?: number
  created_at?: string
}

export interface PersonBrief {
  id: number
  full_name: string
  email?: string
  role?: string
}

export interface CaseAction {
  id: number
  action_type: string
  description: string
  old_status?: string | null
  new_status?: string | null
  performed_by?: PersonBrief | null
  created_at: string
}

export interface Case {
  id: number
  case_number: string
  source_case_id?: string | null
  title: string
  summary?: string | null
  category: string
  sub_category?: string | null
  status: string
  priority: string
  institution_id: number
  institution?: { id: number; canonical_name: string; state?: string | null } | null
  bureau_id?: number | null
  bureau?: { id: number; code: string; name: string } | null
  assigned_officer_id?: number | null
  assigned_officer?: PersonBrief | null
  complainant_name?: string | null
  complainant_email?: string | null
  complainant_phone?: string | null
  can_act?: boolean
  received_date?: string | null
  due_date?: string | null
  disposed_date?: string | null
  next_action?: string | null
  last_action?: string | null
  last_action_date?: string | null
  overlap_bureaus?: string[]
  actions?: CaseAction[]
  created_at?: string
  updated_at?: string
}

export interface CaseRelationship {
  id: number
  case_a_id: number
  case_b_id: number
  case_a?: { id: number; case_number: string; title: string; category: string; status: string } | null
  case_b?: { id: number; case_number: string; title: string; category: string; status: string } | null
  relationship_type: string
  score?: number | null
  reasons?: string[] | null
  matching_evidence?: Record<string, unknown> | null
  algorithm_version?: string | null
  review_status: string
  created_at?: string
}

export interface CoordinationParticipant {
  id: number
  bureau_id?: number | null
  user_id?: number | null
  role_in_coordination?: string | null
  acknowledged: boolean
  acknowledged_at?: string | null
}

export interface CoordinationTask {
  id: number
  title: string
  description?: string | null
  assigned_to_id?: number | null
  due_date?: string | null
  is_completed: boolean
  completed_at?: string | null
  completion_notes?: string | null
  created_at?: string | null
}

export interface CoordinationItem {
  id: number
  reference_number: string
  title: string
  description?: string | null
  status: string
  decision?: string | null
  decision_rationale?: string | null
  owner_id?: number | null
  acknowledge_by?: string | null
  action_due_date?: string | null
  closure_notes?: string | null
  is_exception_closure?: boolean
  institution_id?: number | null
  lead_bureau_id?: number | null
  created_at?: string | null
  updated_at?: string | null
  participants: CoordinationParticipant[]
  tasks: CoordinationTask[]
}

export interface Notification {
  id: number
  title: string
  message: string
  notification_type?: string | null
  priority: string
  is_read: boolean
  link_url?: string | null
  related_case_id?: number | null
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

// ─── Intelligence ─────────────────────────────────────────────────────────────

export interface RuleHit {
  code: string
  title: string
  explanation: string
  severity: string
}

export interface PairAnalysis {
  case_a_id: number
  case_b_id: number
  case_a_number: string
  case_b_number: string
  bureau_a: string
  bureau_b: string
  cross_bureau: boolean
  classification: 'duplicate' | 'action_conflict' | 'related_pattern' | 'independent'
  headline: string
  severity: string
  text_similarity: number
  shared_issues: string[]
  same_complainant: boolean
  reasons: string[]
  rules: RuleHit[]
}

export interface LeadBureau {
  bureau_code: string
  bureau_id: number | null
  bureau_name: string
  score: number
  reasons: string[]
  supporting_bureaus: string[]
  protocol: string[]
}

export interface OverlapAnalysis {
  ruleset: string
  banner: string | null
  coordination_required: boolean
  severity: string
  active_bureaus: string[]
  bureaus_involved: string[]
  classification_counts: Record<string, number>
  pairs: PairAnalysis[]
  lead_bureau: LeadBureau | null
  recommended_actions: string[]
}

export interface CaseBrief {
  id: number
  case_number: string
  source_case_id?: string | null
  title: string
  category: string
  status: string
  priority: string
  bureau_id: number | null
  bureau_code: string | null
  bureau_name: string | null
  officer: string | null
  received_date: string | null
  due_date: string | null
  last_action: string | null
  last_action_date: string | null
  next_action: string | null
}

export interface InstitutionBrief {
  id: number
  canonical_name: string
  short_name?: string | null
  city?: string | null
  state?: string | null
  region?: string | null
  aicte_id?: string | null
}

export interface OverlapCluster {
  institution: InstitutionBrief
  case_count: number
  open_case_count: number
  cases: CaseBrief[]
  analysis: OverlapAnalysis
  coordination: { id: number; reference_number: string; status: string; lead_bureau_id: number | null } | null
}

export interface RiskFactor {
  code: string
  label: string
  points: number
  detail: string
}

export interface RiskProfile {
  score: number
  level: 'critical' | 'high' | 'elevated' | 'low'
  factors: RiskFactor[]
  systemic_issues: { issue: string; label: string; count: number }[]
  recommendations: string[]
  complaints_90d: number
  open_cases: number
  overdue_cases: number
}

export interface ResolveCandidate {
  institution_id: number
  canonical_name: string
  short_name?: string | null
  city?: string | null
  state?: string | null
  region?: string | null
  aicte_id?: string | null
  confidence: number
  band: 'confirmed' | 'high' | 'probable' | 'weak'
  evidence: { signal: string; detail: string; strength: number }[]
  conflicts: string[]
}

export interface ResolveResult {
  engine: string
  signals: {
    normalized_text: string
    aicte_ids: string[]
    aishe_ids: string[]
    pincodes: string[]
    domains: string[]
    phones: string[]
    transliterated: boolean
  }
  candidates: ResolveCandidate[]
  ambiguous: boolean
  decision: 'auto_link_suggested' | 'human_confirmation_required' | 'no_match'
  note: string
  registry_size: number
}
