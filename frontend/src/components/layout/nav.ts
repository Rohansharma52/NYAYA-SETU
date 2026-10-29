import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard, Radar, Activity, FolderKanban, FilePlus2, Building2, ArrowLeftRight, GitMerge, ClipboardCheck,
  BarChart3, Fingerprint, Upload, Users, ScrollText, Bell, LifeBuoy,
} from 'lucide-react'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  group: string
  hint?: string
  roles?: string[]
  badge?: 'overlaps' | 'transfers' | 'reviews'
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Command Centre', icon: LayoutDashboard, group: 'Monitor', hint: 'Single-window overview' },
  { to: '/overlaps', label: 'Overlap Radar', icon: Radar, group: 'Monitor', hint: 'Cross-bureau overlaps & conflicts', badge: 'overlaps' },
  { to: '/risk', label: 'Risk Radar', icon: Activity, group: 'Monitor', hint: 'Institution risk from complaint patterns' },
  { to: '/cases', label: 'All Cases', icon: FolderKanban, group: 'Cases', hint: 'Search & filter every complaint' },
  { to: '/cases/new', label: 'Register Complaint', icon: FilePlus2, group: 'Cases', hint: 'With live identity resolution' },
  { to: '/institutions', label: 'Institutions', icon: Building2, group: 'Cases', hint: 'Institution 360° profiles' },
  { to: '/transfers', label: 'Transfers', icon: ArrowLeftRight, group: 'Cases', hint: 'Accept or reject transfer requests', badge: 'transfers' },
  { to: '/coordination', label: 'Coordination', icon: GitMerge, group: 'Coordinate', hint: 'One Institution, One Voice' },
  { to: '/relationships', label: 'Review Inbox', icon: ClipboardCheck, group: 'Coordinate', hint: 'Confirm or reject suggested links', badge: 'reviews' },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3, group: 'Insight', hint: 'Bureau, region, monthly & quarterly' },
  { to: '/identity-lab', label: 'Identity Lab', icon: Fingerprint, group: 'Insight', hint: 'Engine demo & accuracy benchmark' },
  { to: '/notifications', label: 'Alerts', icon: Bell, group: 'Insight', hint: 'Timeline, escalation & overlap alerts' },
  { to: '/imports', label: 'Data Imports', icon: Upload, group: 'Administration', roles: ['data_admin', 'system_admin'], hint: 'CSV / CPGRAMS ingestion' },
  { to: '/admin/users', label: 'Users & Access', icon: Users, group: 'Administration', roles: ['system_admin'] },
  { to: '/admin/audit', label: 'Audit Trail', icon: ScrollText, group: 'Administration', roles: ['system_admin', 'senior_management'] },
  { to: '/help', label: 'Help & Demo Guide', icon: LifeBuoy, group: 'Administration' },
]
