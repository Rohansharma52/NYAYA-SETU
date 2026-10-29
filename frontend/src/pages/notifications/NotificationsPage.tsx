import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlarmClock, ArrowLeftRight, BellRing, CheckCheck, GitMerge, Hourglass, Radar, TrendingUp, UserCheck } from 'lucide-react'
import { listNotifications, markAllRead, markRead } from '../../api/notifications'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, EmptyState, ErrorState, Segmented, TableSkeleton } from '../../components/ui'
import { fmtDateTime, fromNow } from '../../lib/format'
import { cn } from '../../lib/cn'

const TYPES: Record<string, { label: string; icon: typeof BellRing; tone: string }> = {
  overlap: { label: 'Overlap', icon: Radar, tone: 'bg-rose-50 text-rose-600' },
  sla_breach: { label: 'Timeline breached', icon: AlarmClock, tone: 'bg-rose-50 text-rose-600' },
  sla_approaching: { label: 'Approaching timeline', icon: Hourglass, tone: 'bg-amber-50 text-amber-600' },
  pending_reminder: { label: 'Pending reminder', icon: BellRing, tone: 'bg-sky-50 text-sky-600' },
  escalation: { label: 'Escalation', icon: TrendingUp, tone: 'bg-orange-50 text-orange-600' },
  transfer: { label: 'Transfer', icon: ArrowLeftRight, tone: 'bg-cyan-50 text-cyan-600' },
  coordination: { label: 'Coordination', icon: GitMerge, tone: 'bg-gold-50 text-gold-700' },
  case_assigned: { label: 'Assignment', icon: UserCheck, tone: 'bg-royal-50 text-royal-600' },
}

export default function NotificationsPage() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [type, setType] = useState('')
  const q = useQuery({ queryKey: ['notifications', 'page', filter], queryFn: () => listNotifications({ unread_only: filter === 'unread', limit: 200 }) })
  const all = useMutation({ mutationFn: markAllRead, onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }) })
  const items = (q.data?.items ?? []).filter((n) => !type || n.notification_type === type)
  const counts: Record<string, number> = {}
  for (const n of q.data?.items ?? []) counts[n.notification_type ?? 'other'] = (counts[n.notification_type ?? 'other'] ?? 0) + 1
  return (
    <div>
      <PageHeader eyebrow="Alerts & notifications" title="Alerts"
        description="Duplicate/overlap alerts, pending-case reminders, escalation alerts and timeline (SLA) alerts — generated automatically every 15 minutes."
        actions={<><Segmented value={filter} onChange={setFilter} options={[{ value: 'all', label: 'All' }, { value: 'unread', label: 'Unread' }]} /><Button variant="secondary" leftIcon={<CheckCheck className="h-4 w-4" />} onClick={() => all.mutate()}>Mark all read</Button></>} />
      <div className="mb-5 flex flex-wrap gap-2">
        <button onClick={() => setType('')} className={cn('chip h-8 px-3 text-xs', !type ? 'border-ink-900 bg-ink-900 text-white' : 'border-slate-200 bg-white text-slate-600')}>All types</button>
        {Object.entries(TYPES).filter(([k]) => counts[k]).map(([k, t]) => (
          <button key={k} onClick={() => setType(k)} className={cn('chip h-8 px-3 text-xs', type === k ? 'border-ink-900 bg-ink-900 text-white' : 'border-slate-200 bg-white text-slate-600')}>
            <t.icon className="h-3.5 w-3.5" />{t.label} · {counts[k]}
          </button>
        ))}
      </div>
      <Card noPadding>
        {q.isLoading ? <TableSkeleton /> : q.isError ? <ErrorState onRetry={() => q.refetch()} /> : items.length === 0 ? <EmptyState icon={BellRing} title="No alerts" description="You're all caught up." /> : (
          <ul className="divide-y divide-slate-100">
            {items.map((n, i) => {
              const t = TYPES[n.notification_type ?? ''] ?? { label: 'Info', icon: BellRing, tone: 'bg-slate-100 text-slate-600' }
              return (
                <li key={n.id} style={{ animation: `fade-up .4s var(--ease-out) ${Math.min(i, 10) * 0.03}s both` }}>
                  <button onClick={async () => { if (!n.is_read) await markRead(n.id).catch(() => undefined); qc.invalidateQueries({ queryKey: ['notifications'] }); if (n.link_url) navigate(n.link_url) }}
                    className={cn('flex w-full items-start gap-4 px-5 py-4 text-left transition hover:bg-slate-50', !n.is_read && 'bg-royal-50/30')}>
                    <span className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-xl', t.tone)}><t.icon className="h-5 w-5" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2"><span className="text-sm font-bold text-slate-900">{n.title}</span>{!n.is_read && <span className="h-2 w-2 rounded-full bg-royal-500" />}</span>
                      <span className="mt-0.5 block text-[13px] text-slate-600">{n.message}</span>
                      <span className="mt-1 block text-xs text-slate-400" title={fmtDateTime(n.created_at)}>{t.label} · {fromNow(n.created_at)}</span>
                    </span>
                    <span className={cn('chip shrink-0', n.priority === 'urgent' ? 'border-rose-200 bg-rose-50 text-rose-700' : n.priority === 'high' ? 'border-orange-200 bg-orange-50 text-orange-700' : 'border-slate-200 bg-slate-50 text-slate-500')}>{n.priority}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </Card>
    </div>
  )
}
