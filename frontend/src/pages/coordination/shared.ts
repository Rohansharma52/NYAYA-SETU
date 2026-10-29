export const COORD_STATUS: Record<string, { label: string; chip: string }> = {
  detected: { label: 'Detected', chip: 'border-slate-200 bg-slate-50 text-slate-600' },
  under_review: { label: 'Under review', chip: 'border-sky-200 bg-sky-50 text-sky-700' },
  active: { label: 'Active', chip: 'border-royal-200 bg-royal-50 text-royal-700' },
  acknowledged: { label: 'Acknowledged', chip: 'border-indigo-200 bg-indigo-50 text-indigo-700' },
  follow_up: { label: 'Follow-up', chip: 'border-amber-200 bg-amber-50 text-amber-700' },
  closure_review: { label: 'Closure review', chip: 'border-violet-200 bg-violet-50 text-violet-700' },
  closed: { label: 'Closed', chip: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
  dismissed: { label: 'Dismissed', chip: 'border-slate-200 bg-slate-100 text-slate-500' },
  escalated: { label: 'Escalated', chip: 'border-rose-200 bg-rose-50 text-rose-700' },
}
