import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis,
} from 'recharts'
import {
  AlarmClock, ArrowRight, CheckCircle2, Clock3, FilePlus2, Gauge, GitMerge, Hourglass, Inbox, Layers, Radar,
  ShieldAlert, Shuffle, TrendingUp, Zap,
} from 'lucide-react'
import { getOverview } from '../../api/analytics'
import { getPulse, listOverlaps } from '../../api/intelligence'
import { useAuth } from '../../contexts/AuthContext'
import { useBureaus, useDocumentTitle } from '../../hooks/useData'
import { bureauStyle, REGIONS, ROLE_LABELS } from '../../lib/domain'
import { fmtDate, fromNow } from '../../lib/format'
import { cn } from '../../lib/cn'
import {
  BureauChip, ButtonLink, Card, DataNote, EmptyState, ErrorState, LiveDot, Meter, PageSkeleton, ScoreRing,
  SeverityBadge, StatCard, Timeline,
} from '../../components/ui'

function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

const tooltipStyle = {
  borderRadius: 12,
  border: '1px solid #E2E8F0',
  boxShadow: '0 10px 30px -12px rgba(16,24,64,.25)',
  fontSize: 12,
  padding: '8px 12px',
}

export default function DashboardPage() {
  useDocumentTitle('Command Centre')
  const { user } = useAuth()
  const navigate = useNavigate()
  const { bureaus } = useBureaus()
  const [bureauId, setBureauId] = useState<number | undefined>()
  const [region, setRegion] = useState<string>('')
  const isOfficer = user?.role === 'bureau_officer'

  const ov = useQuery({
    queryKey: ['overview', bureauId, region],
    queryFn: () => getOverview({ bureau_id: bureauId, region: region || undefined }),
    refetchInterval: 30000,
  })
  const overlaps = useQuery({ queryKey: ['overlaps', 'dash'], queryFn: () => listOverlaps({ limit: 12 }), refetchInterval: 30000 })
  const pulse = useQuery({ queryKey: ['pulse'], queryFn: () => getPulse(12), refetchInterval: 10000 })

  const trendReceived = useMemo(() => ov.data?.trend.map((t) => t.received) ?? [], [ov.data])
  const trendDisposed = useMemo(() => ov.data?.trend.map((t) => t.disposed) ?? [], [ov.data])

  if (ov.isLoading) return <PageSkeleton />
  if (ov.isError || !ov.data) return <ErrorState onRetry={() => ov.refetch()} />
  const d = ov.data
  const s = overlaps.data?.summary
  const topClusters = (overlaps.data?.items ?? []).filter((c) => c.analysis.severity !== 'low').slice(0, 4)
  const maxWork = Math.max(1, ...d.bureau_workload.map((b) => b.total))

  return (
    <div className="space-y-6">
      {/* Hero */}
      <section className="bg-hero relative overflow-hidden rounded-3xl p-6 text-white shadow-lift sm:p-8">
        <div className="absolute inset-0 bg-grid opacity-40 [mask-image:linear-gradient(to_bottom,#000,transparent)]" />
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full border border-white/10" />
        <div className="absolute -right-10 -top-10 h-44 w-44 rounded-full border border-gold-300/20 animate-spin-slow" />
        <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-2xl">
            <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-royal-200/80">
              <LiveDot /> Command Centre · {fmtDate(new Date(), 'EEEE, dd MMMM yyyy')}
            </p>
            <h1 className="mt-3 text-[28px] font-extrabold leading-tight text-white sm:text-[34px]">
              {greeting()}, <span className="text-gradient-gold">{user?.full_name?.split(' ').slice(0, 2).join(' ')}</span>
            </h1>
            <p className="mt-2 text-sm text-royal-100/75 sm:text-[15px]">
              {s && s.institutions > 0 ? (
                <>
                  <b className="text-white">{s.institutions} institutions</b> are being handled by more than one Bureau/Cell —{' '}
                  <b className="text-rose-300">{s.critical} critical</b> and <b className="text-orange-300">{s.high} high</b> need coordination.
                </>
              ) : (
                'No cross-bureau overlaps need attention right now.'
              )}{' '}
              {d.pending_beyond_timeline > 0 && (
                <>
                  <b className="text-gold-300">{d.pending_beyond_timeline} cases</b> are past their prescribed timeline.
                </>
              )}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <ButtonLink to="/overlaps" variant="gold" leftIcon={<Radar className="h-4 w-4" />}>Open Overlap Radar</ButtonLink>
              <ButtonLink to="/cases/new" variant="dark" leftIcon={<FilePlus2 className="h-4 w-4" />}>Register complaint</ButtonLink>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 sm:min-w-[440px]">
            {[
              { label: 'Conflicts', value: s?.conflicts ?? 0, tone: 'text-rose-300', icon: ShieldAlert },
              { label: 'Duplicates', value: s?.duplicates ?? 0, tone: 'text-violet-300', icon: Layers },
              { label: 'Awaiting lead', value: s?.awaiting_coordination ?? 0, tone: 'text-gold-300', icon: GitMerge },
            ].map((m) => (
              <div key={m.label} className="glass rounded-2xl p-4">
                <m.icon className={cn('h-4 w-4', m.tone)} />
                <p className="mt-3 text-3xl font-extrabold tabular">{m.value}</p>
                <p className="text-[11px] font-medium text-white/55">{m.label}</p>
              </div>
            ))}
          </div>
        </div>
        {/* live ticker */}
        {(pulse.data?.events?.length ?? 0) > 0 && (
          <div className="relative mt-6 flex items-center gap-3 rounded-xl border border-white/10 bg-white/[.04] px-3 py-2">
            <span className="flex shrink-0 items-center gap-1.5 rounded-md bg-emerald-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-emerald-300">
              <Zap className="h-3 w-3" /> Live
            </span>
            <div className="mask-fade-x relative flex-1 overflow-hidden">
              <div
                className="flex w-max animate-marquee gap-8 whitespace-nowrap text-xs text-white/70 hover:[animation-play-state:paused]"
                // ~7 s per update keeps the ticker readable whatever the number of events
                style={{ animationDuration: `${Math.max(60, (pulse.data?.events?.length ?? 0) * 7)}s` }}
              >
                {[...(pulse.data?.events ?? []), ...(pulse.data?.events ?? [])].map((e, i) => (
                  <Link key={`${e.id}-${i}`} to={`/cases/${e.case_id}`} className="inline-flex items-center gap-2 hover:text-white">
                    <span className="font-bold" style={{ color: bureauStyle(e.bureau_code).color === '#64748B' ? '#cbd5e1' : '#FDE08A' }}>{e.bureau_code}</span>
                    <span className="font-mono text-white/40">{e.case_number}</span>
                    <span>{e.institution} — {e.description.slice(0, 70)}</span>
                    <span className="text-white/35">{fromNow(e.created_at)}</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Filters */}
      {!isOfficer && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="label-eyebrow mr-1">Scope</span>
          <button onClick={() => setBureauId(undefined)} className={cn('chip h-7 px-3 text-xs', !bureauId ? 'border-ink-900 bg-ink-900 text-white' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300')}>
            All Bureaus / Cells
          </button>
          {bureaus.map((b) => {
            const st = bureauStyle(b.code)
            const on = bureauId === b.id
            return (
              <button
                key={b.id}
                onClick={() => setBureauId(on ? undefined : b.id)}
                className="chip h-7 px-3 text-xs transition"
                style={on ? { background: st.color, color: '#fff', borderColor: st.color } : { background: '#fff', color: st.color, borderColor: `${st.color}40` }}
              >
                {b.code}
              </button>
            )
          })}
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="ml-auto h-8 rounded-lg border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-600 focus:outline-none focus:ring-2 focus:ring-royal-100">
            <option value="">All regions</option>
            {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      )}

      {/* KPI tiles required by PS §4 */}
      <div className="stagger grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total received" value={d.totals.received} icon={<Inbox className="h-5 w-5" />} accent="royal" trend={trendReceived} to="/cases" hint="All complaints in scope" />
        <StatCard label="Pending" value={d.totals.pending} icon={<Hourglass className="h-5 w-5" />} accent="slate" to="/cases?group=pending" hint="Received · triaged · assigned" />
        <StatCard label="Under process" value={d.totals.under_process} icon={<Clock3 className="h-5 w-5" />} accent="violet" to="/cases?group=under_process" hint="Being examined" />
        <StatCard label="Disposed" value={d.totals.disposed} icon={<CheckCircle2 className="h-5 w-5" />} accent="emerald" trend={trendDisposed} to="/cases?group=disposed" hint={`${d.disposal_rate}% disposal rate`} />
        <StatCard label="Transferred" value={d.totals.transferred} icon={<Shuffle className="h-5 w-5" />} accent="cyan" to="/transfers" hint="Requested or completed" />
        <StatCard label="Escalated" value={d.totals.escalated} icon={<TrendingUp className="h-5 w-5" />} accent="orange" to="/cases?status=escalated" hint="Needs senior attention" />
        <StatCard label="Beyond timeline" value={d.pending_beyond_timeline} icon={<AlarmClock className="h-5 w-5" />} accent="rose" to="/cases?overdue=1" hint="Pending past expected disposal" />
        <StatCard label="Due in 7 days" value={d.approaching_timeline} icon={<Gauge className="h-5 w-5" />} accent="gold" to="/cases?group=pending" hint="Approaching prescribed timeline" />
      </div>

      {/* Overlaps + performance */}
      <div className="grid gap-6 xl:grid-cols-3">
        <Card
          className="xl:col-span-2"
          icon={<Radar className="h-5 w-5" />}
          title="Potential Overlapping Cases – Coordination Required"
          subtitle="Institutions where RB, PGRC or other Bureaus/Cells are acting in parallel"
          action={<ButtonLink to="/overlaps" size="sm" variant="secondary" rightIcon={<ArrowRight className="h-3.5 w-3.5" />}>View all</ButtonLink>}
        >
          {topClusters.length === 0 ? (
            <EmptyState icon={GitMerge} title="No overlaps need action" description="All multi-bureau institutions are coordinated." />
          ) : (
            <div className="space-y-2.5">
              {topClusters.map((c) => (
                <button
                  key={c.institution.id}
                  onClick={() => navigate(`/overlaps?institution=${c.institution.id}`)}
                  className="group flex w-full items-center gap-4 rounded-2xl border border-slate-200/80 bg-white p-3.5 text-left transition hover:-translate-y-0.5 hover:border-royal-200 hover:shadow-card"
                >
                  <span className={cn('h-10 w-1.5 shrink-0 rounded-full bg-gradient-to-b', c.analysis.severity === 'critical' ? 'from-rose-500 to-rose-400' : c.analysis.severity === 'high' ? 'from-orange-500 to-amber-400' : 'from-amber-400 to-yellow-300')} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-bold text-slate-900">{c.institution.canonical_name}</p>
                      <SeverityBadge severity={c.analysis.severity} />
                    </div>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {c.analysis.pairs[0]?.headline} · {c.open_case_count} open cases
                    </p>
                  </div>
                  <div className="hidden items-center gap-1 sm:flex">
                    {c.analysis.active_bureaus.map((b) => <BureauChip key={b} code={b} />)}
                  </div>
                  <div className="hidden w-32 text-right md:block">
                    {c.coordination ? (
                      <span className="text-xs font-semibold text-emerald-600">{c.coordination.reference_number}</span>
                    ) : c.analysis.lead_bureau ? (
                      <span className="text-xs text-slate-500">Lead: <b className="text-slate-800">{c.analysis.lead_bureau.bureau_code}</b></span>
                    ) : null}
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-300 transition group-hover:translate-x-0.5 group-hover:text-royal-500" />
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card title="Disposal performance" subtitle="Across the selected scope" icon={<Gauge className="h-5 w-5" />}>
          <div className="flex items-center justify-around py-2">
            <ScoreRing value={d.disposal_rate} label={`${Math.round(d.disposal_rate)}%`} sublabel="disposed" color="#10B981" size={104} />
            <ScoreRing value={d.on_time_disposal_rate ?? 0} label={d.on_time_disposal_rate === null ? '—' : `${Math.round(d.on_time_disposal_rate)}%`} sublabel="on time" color="#5B66EC" size={104} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-[11px] font-semibold text-slate-500">Avg. time to dispose</p>
              <p className="mt-1 text-xl font-extrabold text-slate-900 tabular">{d.avg_disposal_days ?? '—'}<span className="text-sm font-semibold text-slate-400"> days</span></p>
            </div>
            <div className="rounded-xl bg-slate-50 p-3">
              <p className="text-[11px] font-semibold text-slate-500">Open right now</p>
              <p className="mt-1 text-xl font-extrabold text-slate-900 tabular">{d.totals.pending + d.totals.under_process + d.totals.escalated}</p>
            </div>
          </div>
          <Link to="/reports" className="mt-4 flex items-center justify-center gap-1 text-xs font-semibold text-royal-600 hover:text-royal-800">
            Monthly & quarterly performance <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </Card>
      </div>

      {/* Workload + trend */}
      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-2" title="Bureau / Cell workload" subtitle="Open, overdue and disposed by Bureau/Cell" icon={<Layers className="h-5 w-5" />}>
          <div className="space-y-4">
            {d.bureau_workload.map((b) => {
              const st = bureauStyle(b.code)
              return (
                <div key={b.bureau_id}>
                  <div className="mb-1.5 flex items-center justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-2">
                      <BureauChip code={b.code} />
                      <span className="truncate text-xs text-slate-500">{b.name}</span>
                    </div>
                    <span className="text-xs text-slate-500 tabular">
                      <b className="text-slate-800">{b.open}</b> open · <b className={b.overdue ? 'text-rose-600' : 'text-slate-800'}>{b.overdue}</b> overdue
                    </span>
                  </div>
                  <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                    <div style={{ width: `${(b.open - b.overdue) / maxWork * 100}%`, background: st.color, transition: 'width 1s' }} />
                    <div style={{ width: `${b.overdue / maxWork * 100}%` }} className="bg-rose-500" />
                    <div style={{ width: `${b.disposed / maxWork * 100}%`, background: `${st.color}40` }} />
                  </div>
                </div>
              )
            })}
            <div className="flex items-center gap-4 pt-1 text-[11px] text-slate-500">
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-royal-500" />Open</span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-rose-500" />Overdue</span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-royal-200" />Disposed</span>
            </div>
          </div>
        </Card>

        <Card className="xl:col-span-3" title="Receipt vs disposal" subtitle="Last 12 months" icon={<TrendingUp className="h-5 w-5" />}>
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={d.trend} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="gRec" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#5B66EC" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#5B66EC" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gDis" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10B981" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#EEF1F7" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                <RTooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="received" name="Received" stroke="#5B66EC" strokeWidth={2.5} fill="url(#gRec)" animationDuration={1200} />
                <Area type="monotone" dataKey="disposed" name="Disposed" stroke="#10B981" strokeWidth={2.5} fill="url(#gDis)" animationDuration={1400} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Institutions + ageing + live feed */}
      <div className="grid gap-6 xl:grid-cols-5">
        <Card className="xl:col-span-3" title="Institution-wise case status" subtitle="Institutions with the most open cases" noPadding>
          <div className="overflow-x-auto px-2 pb-2">
            <table className="table-modern w-full min-w-[640px]">
              <thead>
                <tr>
                  <th>Institution</th>
                  <th>Bureaus</th>
                  <th className="text-right">Open</th>
                  <th className="text-right">Overdue</th>
                  <th className="w-28">Disposed</th>
                </tr>
              </thead>
              <tbody>
                {d.institutions.map((r) => (
                  <tr key={r.institution_id} className="cursor-pointer" onClick={() => navigate(`/institutions/${r.institution_id}`)}>
                    <td>
                      <p className="font-semibold text-slate-800">{r.short_name ?? r.name}</p>
                      <p className="max-w-[260px] truncate text-xs text-slate-400">{r.name} · {r.region}</p>
                    </td>
                    <td><div className="flex gap-1">{r.bureaus.map((b) => <BureauChip key={b} code={b} />)}</div></td>
                    <td className="text-right font-bold tabular">{r.open}</td>
                    <td className={cn('text-right font-bold tabular', r.overdue ? 'text-rose-600' : 'text-slate-400')}>{r.overdue}</td>
                    <td><Meter value={r.disposed} max={r.total} barClassName="from-emerald-500 to-emerald-400" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="space-y-6 xl:col-span-2">
          <Card title="Pending case ageing" subtitle="Open cases by age">
            <div className="h-[170px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={d.ageing} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                  <CartesianGrid stroke="#EEF1F7" vertical={false} />
                  <XAxis dataKey="bucket" tick={{ fontSize: 10.5, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                  <RTooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(91,102,236,.06)' }} />
                  <Bar dataKey="count" name="Open cases" radius={[8, 8, 0, 0]} animationDuration={1100}>
                    {d.ageing.map((_, i) => <Cell key={i} fill={['#A3AEFB', '#7C88F5', '#5B66EC', '#F59E0B', '#E11D48'][i]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title={<span className="flex items-center gap-2">Live activity <LiveDot /></span>} subtitle={`Across ${isOfficer ? 'your bureau' : 'all Bureaus / Cells'}`}>
            <div className="max-h-[300px] overflow-y-auto pr-1">
              <Timeline
                compact
                events={(pulse.data?.events ?? []).slice(0, 7).map((e) => ({
                  id: e.id, type: e.action_type, description: `${e.institution ?? ''} — ${e.description}`,
                  performedBy: e.performed_by, createdAt: e.created_at, bureau: e.bureau_code, caseNumber: e.case_number,
                }))}
              />
            </div>
          </Card>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <DataNote />
        <p className="text-[11px] text-slate-400">Scope: {ROLE_LABELS[user?.role ?? '']} · refreshed {fromNow((d as unknown as { generated_at: string }).generated_at)}</p>
      </div>
    </div>
  )
}
