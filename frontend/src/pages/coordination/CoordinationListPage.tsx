import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CalendarClock, Crown, GitMerge, Plus } from 'lucide-react'
import { listCoordination } from '../../api/coordination'
import { PageHeader } from '../../components/layout/PageHeader'
import { BureauChip, ButtonLink, Card, EmptyState, ErrorState, Meter, Segmented, SkeletonCard } from '../../components/ui'
import { useBureaus } from '../../hooks/useData'
import { daysUntil, fmtDate } from '../../lib/format'
import { cn } from '../../lib/cn'
import { COORD_STATUS } from './shared'

type F = 'open' | 'closed' | 'all'

export default function CoordinationListPage() {
  const navigate = useNavigate()
  const { byId } = useBureaus()
  const [f, setF] = useState<F>('open')
  const q = useQuery({ queryKey: ['coordination'], queryFn: () => listCoordination({ limit: 200 }) })
  const items = (q.data?.items ?? []).filter((c) => f === 'all' || (f === 'closed' ? ['closed', 'dismissed'].includes(c.status) : !['closed', 'dismissed'].includes(c.status)))
  return (
    <div>
      <PageHeader
        eyebrow="Coordination Closure Protocol"
        title="Coordination"
        description="One Institution, One Voice — a lead bureau, supporting bureaus, acknowledgements, follow-up tasks and a recorded closure. Coordination never closes a bureau's own case."
        actions={<>
          <Segmented<F> value={f} onChange={setF} options={[{ value: 'open', label: 'Open' }, { value: 'closed', label: 'Closed' }, { value: 'all', label: 'All' }]} />
          <ButtonLink to="/coordination/new" leftIcon={<Plus className="h-4 w-4" />}>New coordination</ButtonLink>
        </>}
      />
      {q.isLoading ? <div className="grid gap-4 lg:grid-cols-2">{[1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)}</div>
        : q.isError ? <ErrorState onRetry={() => q.refetch()} />
          : items.length === 0 ? <Card><EmptyState icon={GitMerge} title="No coordination items" description="Open one from the Overlap Radar with a single click." action={<ButtonLink to="/overlaps" variant="secondary">Go to Overlap Radar</ButtonLink>} /></Card>
            : (
              <div className="stagger grid gap-4 lg:grid-cols-2">
                {items.map((c) => {
                  const lead = c.lead_bureau_id ? byId.get(c.lead_bureau_id) : undefined
                  const bureauParts = c.participants.filter((p) => p.bureau_id)
                  const acked = bureauParts.filter((p) => p.acknowledged).length
                  const tasksDone = c.tasks.filter((t) => t.is_completed).length
                  const due = daysUntil(c.action_due_date)
                  const st = COORD_STATUS[c.status] ?? COORD_STATUS.detected
                  return (
                    <button key={c.id} onClick={() => navigate(`/coordination/${c.id}`)} className="card card-hover p-5 text-left">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="font-mono text-[11px] text-slate-400">{c.reference_number}</p>
                          <p className="mt-0.5 truncate text-[15px] font-bold text-slate-900">{c.title}</p>
                        </div>
                        <span className={cn('chip', st.chip)}>{st.label}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-1.5">
                        {lead && <span className="chip border-gold-200 bg-gold-50 text-gold-700"><Crown className="h-3 w-3" />Lead {lead.code}</span>}
                        {bureauParts.filter((p) => p.bureau_id !== c.lead_bureau_id).map((p) => <BureauChip key={p.id} code={byId.get(p.bureau_id!)?.code} />)}
                      </div>
                      <div className="mt-4 grid grid-cols-2 gap-4">
                        <div>
                          <p className="mb-1 flex justify-between text-[11px] text-slate-500"><span>Acknowledged</span><b className="text-slate-700">{acked}/{bureauParts.length}</b></p>
                          <Meter value={acked} max={Math.max(bureauParts.length, 1)} />
                        </div>
                        <div>
                          <p className="mb-1 flex justify-between text-[11px] text-slate-500"><span>Tasks</span><b className="text-slate-700">{tasksDone}/{c.tasks.length}</b></p>
                          <Meter value={tasksDone} max={Math.max(c.tasks.length, 1)} barClassName="from-emerald-500 to-emerald-400" />
                        </div>
                      </div>
                      <p className={cn('mt-4 flex items-center gap-1.5 text-xs', due !== null && due < 0 && !['closed', 'dismissed'].includes(c.status) ? 'font-semibold text-rose-600' : 'text-slate-500')}>
                        <CalendarClock className="h-3.5 w-3.5" /> Action due {fmtDate(c.action_due_date)}{due !== null && !['closed', 'dismissed'].includes(c.status) ? ` · ${due < 0 ? `${-due}d overdue` : `${due}d left`}` : ''}
                      </p>
                    </button>
                  )
                })}
              </div>
            )}
    </div>
  )
}
