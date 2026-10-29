import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, Lightbulb, MapPin } from 'lucide-react'
import { getRiskRadar } from '../../api/intelligence'
import { PageHeader } from '../../components/layout/PageHeader'
import { AnimatedNumber, BureauChip, DataNote, ErrorState, PageSkeleton, RiskBadge, ScoreRing, Segmented } from '../../components/ui'
import { RISK_META } from '../../lib/domain'
import { cn } from '../../lib/cn'

type Level = 'all' | 'critical' | 'high' | 'elevated' | 'low'

export default function RiskRadarPage() {
  const navigate = useNavigate()
  const [level, setLevel] = useState<Level>('all')
  const q = useQuery({ queryKey: ['risk'], queryFn: () => getRiskRadar(100) })
  const rows = useMemo(() => (q.data?.items ?? []).filter((r) => level === 'all' || r.risk.level === level), [q.data, level])
  if (q.isLoading) return <PageSkeleton />
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} />
  const lv = q.data.levels
  return (
    <div>
      <PageHeader
        eyebrow="Early warning from complaint patterns"
        title="Risk Radar"
        description="An explainable 0–100 score per institution from complaint velocity, overdue files, multi-bureau exposure, systemic issues, escalations and inter-bureau conflict — turning grievances into regulatory intelligence."
        actions={<Segmented<Level> value={level} onChange={setLevel} options={[{ value: 'all', label: 'All' }, { value: 'critical', label: 'Critical' }, { value: 'high', label: 'High' }, { value: 'elevated', label: 'Elevated' }, { value: 'low', label: 'Low' }]} />}
      />
      <div className="stagger mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        {(['critical', 'high', 'elevated', 'low'] as const).map((k) => (
          <button key={k} onClick={() => setLevel(k)} className={cn('card card-hover p-4 text-left', level === k && 'ring-2 ring-offset-2')} style={level === k ? { ['--tw-ring-color' as string]: RISK_META[k].color } : undefined}>
            <div className="flex items-center justify-between"><RiskBadge level={k} /><span className="h-2 w-2 rounded-full" style={{ background: RISK_META[k].color }} /></div>
            <p className="mt-3 text-3xl font-extrabold text-slate-900"><AnimatedNumber value={lv[k] ?? 0} /></p>
            <p className="text-xs text-slate-500">institutions</p>
          </button>
        ))}
      </div>
      <div className="stagger grid gap-4 lg:grid-cols-2">
        {rows.map((r) => (
          <button key={r.institution.id} onClick={() => navigate(`/institutions/${r.institution.id}`)} className="card card-hover group flex min-w-0 gap-4 p-4 text-left sm:gap-5 sm:p-5">
            <ScoreRing value={r.risk.score} color={RISK_META[r.risk.level].color} size={92} sublabel={RISK_META[r.risk.level].label} />
            <div className="min-w-0 flex-1">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-slate-900 group-hover:text-royal-700">{r.institution.canonical_name}</p>
                  <p className="flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3 w-3" />{r.institution.city} · {r.institution.region}</p>
                </div>
                <div className="flex flex-wrap gap-1">{r.bureaus.map((b) => <BureauChip key={b} code={b} />)}</div>
              </div>
              <div className="mt-3 space-y-1.5">
                {r.risk.factors.slice(0, 4).map((f) => (
                  <div key={f.code} className="flex items-center gap-2">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full" style={{ width: `${Math.min(100, (f.points / 28) * 100)}%`, background: RISK_META[r.risk.level].color }} />
                    </div>
                    <span className="truncate text-[11.5px] text-slate-600"><b>{f.label}</b> — {f.detail}</span>
                  </div>
                ))}
              </div>
              <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-amber-50/70 px-2.5 py-1.5 text-[11.5px] text-amber-800"><Lightbulb className="mt-px h-3.5 w-3.5 shrink-0" />{r.risk.recommendations[0]}</p>
            </div>
          </button>
        ))}
      </div>
      {rows.length === 0 && <div className="card p-10 text-center text-sm text-slate-500"><Activity className="mx-auto mb-2 h-6 w-6 text-slate-300" />No institutions at this level.</div>}
      <div className="mt-6"><DataNote message="Weights are transparent prototype defaults — to be calibrated with AICTE's historical outcomes." /></div>
    </div>
  )
}
