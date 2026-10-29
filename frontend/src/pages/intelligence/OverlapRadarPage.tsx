import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertOctagon, ArrowLeftRight, ArrowRight, BellRing, Building2, CheckCircle2, Crown, GitMerge, Layers, Megaphone,
  Radar, ScanSearch, ShieldAlert, Sparkles,
} from 'lucide-react'
import { getOverlap, listOverlaps, scanAlerts, startCoordination } from '../../api/intelligence'
import { apiError } from '../../api/client'
import { useAuth } from '../../contexts/AuthContext'
import { toast } from '../../hooks/useToast'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  AnimatedNumber, BureauChip, Button, ButtonLink, ClassificationBadge, DataNote, EmptyState, ErrorState, PageSkeleton,
  Segmented, SeverityBadge, StatusBadge,
} from '../../components/ui'
import { bureauStyle, CLASSIFICATION_META } from '../../lib/domain'
import { cn } from '../../lib/cn'
import { daysUntil, fmtDate, fromNow } from '../../lib/format'
import type { CaseBrief, OverlapCluster, PairAnalysis } from '../../types'

type Sev = 'actionable' | 'critical' | 'high' | 'all'

const SEV_BAR: Record<string, string> = {
  critical: 'from-rose-500 to-rose-400',
  high: 'from-orange-500 to-amber-400',
  medium: 'from-amber-400 to-yellow-300',
  low: 'from-slate-300 to-slate-200',
}

function LaneCard({ c }: { c: CaseBrief }) {
  const due = daysUntil(c.due_date)
  const st = bureauStyle(c.bureau_code)
  return (
    <Link
      to={`/cases/${c.id}`}
      className="group block rounded-xl border bg-white p-3 shadow-soft transition hover:-translate-y-0.5 hover:shadow-card"
      style={{ borderColor: `${st.color}30` }}
    >
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <span className="whitespace-nowrap font-mono text-[10.5px] text-slate-400">{c.case_number.replace('AICTE-NS-', '')}</span>
        <StatusBadge status={c.status} />
      </div>
      <p className="mt-1.5 line-clamp-2 text-[13px] font-semibold leading-snug text-slate-800 group-hover:text-royal-700">{c.title}</p>
      {c.last_action && (
        <p className="mt-1.5 line-clamp-2 text-[11.5px] text-slate-500">
          <span className="font-semibold text-slate-600">Last action:</span> {c.last_action}
        </p>
      )}
      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-slate-400">
        <span className="truncate">{c.officer ?? 'Unassigned'}</span>
        {due !== null && !['disposed', 'closed', 'transferred'].includes(c.status) && (
          <span className={cn('shrink-0 font-semibold', due < 0 ? 'text-rose-600' : due <= 7 ? 'text-amber-600' : 'text-slate-500')}>
            {due < 0 ? `${-due}d overdue` : `${due}d left`}
          </span>
        )}
      </div>
    </Link>
  )
}

function PairRow({ p, cases }: { p: PairAnalysis; cases: Map<number, CaseBrief> }) {
  const a = cases.get(p.case_a_id)
  const b = cases.get(p.case_b_id)
  return (
    <div className={cn('rounded-2xl border p-4', p.classification === 'action_conflict' ? 'border-rose-200 bg-rose-50/40' : 'border-slate-200 bg-white')}>
      <div className="flex flex-wrap items-center gap-2">
        <ClassificationBadge value={p.classification} />
        <SeverityBadge severity={p.severity} />
        <span className="text-sm font-bold text-slate-800">{p.headline}</span>
      </div>
      <div className="mt-3 grid items-center gap-2 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        {[a, b].map((c, i) =>
          c ? (
            <Link key={c.id} to={`/cases/${c.id}`} className={cn('min-w-0 rounded-xl border border-slate-200 bg-white p-2.5 transition hover:border-royal-200', i === 1 && 'sm:order-3')}>
              <div className="flex items-center gap-2">
                <BureauChip code={c.bureau_code} />
                <span className="font-mono text-[11px] text-slate-400">{c.case_number}</span>
              </div>
              <p className="mt-1 truncate text-xs font-medium text-slate-700">{c.title}</p>
            </Link>
          ) : null,
        )}
        <div className="flex justify-center sm:order-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-500">
            <ArrowLeftRight className="h-4 w-4" />
          </span>
        </div>
      </div>
      {p.rules.map((r) => (
        <div key={r.code} className="mt-3 flex gap-2.5 rounded-xl bg-white/80 p-3 ring-1 ring-rose-100">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
          <div>
            <p className="text-[12.5px] font-bold text-rose-700">Rule {r.code} · {r.title}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-slate-600">{r.explanation}</p>
          </div>
        </div>
      ))}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {p.reasons.map((r) => (
          <span key={r} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{r}</span>
        ))}
        <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">text similarity {p.text_similarity.toFixed(2)}</span>
      </div>
    </div>
  )
}

function ClusterDetail({ cluster, canAct }: { cluster: OverlapCluster; canAct: boolean }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const a = cluster.analysis
  const caseMap = useMemo(() => new Map(cluster.cases.map((c) => [c.id, c])), [cluster])
  const lanes = useMemo(() => {
    const m = new Map<string, CaseBrief[]>()
    for (const c of cluster.cases) {
      const k = c.bureau_code ?? '—'
      m.set(k, [...(m.get(k) ?? []), c])
    }
    return Array.from(m.entries()).sort((x, y) => (a.lead_bureau?.bureau_code === x[0] ? -1 : a.lead_bureau?.bureau_code === y[0] ? 1 : 0))
  }, [cluster, a.lead_bureau])
  const relevantPairs = a.pairs.filter((p) => p.classification !== 'independent')
  const independent = a.pairs.length - relevantPairs.length

  const coordinate = useMutation({
    mutationFn: () => startCoordination(cluster.institution.id),
    onSuccess: (r) => {
      toast.success(r.message)
      qc.invalidateQueries({ queryKey: ['overlaps'] })
      navigate(`/coordination/${r.id}`)
    },
    onError: (e) => toast.error(apiError(e, 'Could not open coordination')),
  })

  return (
    <div className="space-y-5 animate-fade-in" key={cluster.institution.id}>
      {/* Banner */}
      <div className={cn('relative overflow-hidden rounded-3xl p-5 text-white shadow-lift sm:p-6',
        a.severity === 'critical' ? 'bg-gradient-to-br from-rose-600 via-rose-700 to-ink-900' : a.severity === 'high' ? 'bg-gradient-to-br from-orange-500 via-orange-700 to-ink-900' : 'bg-gradient-to-br from-ink-700 to-ink-900')}>
        <div className="absolute inset-0 bg-grid opacity-25" />
        <div className="absolute -right-6 -top-6 h-36 w-36 rounded-full border-[18px] border-white/5" />
        <div className="relative">
          {a.banner && (
            <p className="inline-flex items-center gap-2 rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ring-1 ring-white/25">
              <AlertOctagon className="h-3.5 w-3.5" /> {a.banner}
            </p>
          )}
          <h2 className="mt-3 text-2xl font-extrabold text-white">{cluster.institution.canonical_name}</h2>
          <p className="mt-1 text-sm text-white/70">
            {cluster.institution.city}, {cluster.institution.state} · {cluster.institution.region} region · AICTE ID{' '}
            <span className="font-mono text-white/90">{cluster.institution.aicte_id ?? '—'}</span>
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {a.active_bureaus.map((b) => <BureauChip key={b} code={b} solid />)}
            <span className="text-xs text-white/60">· {cluster.open_case_count} open of {cluster.case_count} cases</span>
            <Link to={`/institutions/${cluster.institution.id}`} className="ml-auto inline-flex items-center gap-1 text-xs font-semibold text-white/80 hover:text-white">
              <Building2 className="h-3.5 w-3.5" /> Institution 360° <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Lead bureau */}
      {a.lead_bureau && (
        <div className="ring-gradient relative overflow-hidden rounded-3xl border border-gold-200 bg-gradient-to-br from-gold-50 via-white to-white p-5 shadow-soft">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-gold-300 to-gold-500 text-ink-900 shadow-glow-gold">
                <Crown className="h-7 w-7" />
              </div>
              <div>
                <p className="label-eyebrow text-gold-700">Proposed lead bureau</p>
                <p className="text-xl font-extrabold text-slate-900">{a.lead_bureau.bureau_code} <span className="text-sm font-semibold text-slate-500">· {a.lead_bureau.bureau_name}</span></p>
                <p className="text-xs text-slate-500">Supporting: {a.lead_bureau.supporting_bureaus.join(', ') || '—'}</p>
              </div>
            </div>
            <div className="sm:w-64">
              {cluster.coordination ? (
                <ButtonLink to={`/coordination/${cluster.coordination.id}`} variant="success" className="w-full" leftIcon={<GitMerge className="h-4 w-4" />}>
                  Open {cluster.coordination.reference_number}
                </ButtonLink>
              ) : canAct ? (
                <Button variant="gold" className="w-full" size="lg" loading={coordinate.isPending} onClick={() => coordinate.mutate()} leftIcon={<Megaphone className="h-4 w-4" />}>
                  Start One-Voice coordination
                </Button>
              ) : (
                <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">A coordination reviewer or management can open coordination.</p>
              )}
              <p className="mt-1.5 text-center text-[11px] text-slate-400">Advisory — officers confirm. Source files stay unchanged.</p>
            </div>
          </div>
          <div className="mt-4 grid gap-4 border-t border-gold-100 pt-4 lg:grid-cols-[1fr_1.3fr]">
            <div>
              <p className="text-xs font-bold text-slate-700">Why this bureau</p>
              <ul className="mt-1.5 space-y-1">
                {a.lead_bureau.reasons.map((r) => (
                  <li key={r} className="flex gap-2 text-[13px] text-slate-600"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />{r}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-700">One Institution, One Voice protocol</p>
              <ol className="mt-1.5 grid gap-1.5 sm:grid-cols-2">
                {a.lead_bureau.protocol.map((r, i) => (
                  <li key={r} className="flex gap-2 rounded-lg bg-white/80 px-2.5 py-1.5 text-xs text-slate-600 ring-1 ring-slate-100">
                    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-ink-900 text-[9px] font-bold text-white">{i + 1}</span>
                    {r}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      )}

      {/* Swimlanes */}
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900"><Layers className="h-4 w-4 text-royal-500" /> Who is doing what — bureau lanes</h3>
          <p className="text-xs text-slate-400">Every Bureau/Cell file for this institution, side by side</p>
        </div>
        <div className={cn('grid gap-3 sm:grid-cols-2', lanes.length >= 3 && 'xl:grid-cols-3', lanes.length >= 4 && '2xl:grid-cols-4')}>
          {lanes.map(([code, items]) => {
            const st = bureauStyle(code)
            return (
              <div key={code} className="rounded-2xl p-2.5" style={{ background: `${st.color}0d` }}>
                <div className="mb-2 flex items-center justify-between px-1">
                  <BureauChip code={code} />
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-slate-500">
                    {a.lead_bureau?.bureau_code === code && <Crown className="h-3 w-3 text-gold-600" />}
                    {items.length} file{items.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((c) => <LaneCard key={c.id} c={c} />)}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Pair analysis */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900"><ScanSearch className="h-4 w-4 text-royal-500" /> Explainable pair analysis</h3>
        <div className="space-y-3">
          {relevantPairs.map((p) => <PairRow key={`${p.case_a_id}-${p.case_b_id}`} p={p} cases={caseMap} />)}
          {independent > 0 && (
            <p className="rounded-xl border border-dashed border-slate-200 px-4 py-3 text-xs text-slate-500">
              + {independent} pair{independent > 1 ? 's' : ''} classified <b>independent</b> — different issues at the same institution, kept visible to all bureaus.
            </p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="rounded-2xl border border-royal-100 bg-royal-50/50 p-4">
        <p className="flex items-center gap-2 text-sm font-bold text-royal-900"><Sparkles className="h-4 w-4" /> Recommended next steps</p>
        <ul className="mt-2 space-y-1.5">
          {a.recommended_actions.map((r) => (
            <li key={r} className="flex gap-2 text-[13px] text-royal-900/80"><ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0" />{r}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

export default function OverlapRadarPage() {
  const { hasRole } = useAuth()
  const [params, setParams] = useSearchParams()
  const [sev, setSev] = useState<Sev>('actionable')
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['overlaps', 'radar'], queryFn: () => listOverlaps({ limit: 300 }), refetchInterval: 30000 })
  const wantedId = Number(params.get('institution')) || 0
  const inList = (q.data?.items ?? []).some((c) => c.institution.id === wantedId)
  // A linked institution outside the top-300 list is fetched on its own
  const extra = useQuery({ queryKey: ['overlaps', 'one', wantedId], queryFn: () => getOverlap(wantedId), enabled: !!wantedId && !!q.data && !inList, retry: false })
  const scan = useMutation({
    mutationFn: scanAlerts,
    onSuccess: (r) => {
      toast.success(`Alert scan complete — ${r.total} new alerts`)
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (e) => toast.error(apiError(e)),
  })

  const items = useMemo(() => {
    const all = [...(extra.data ? [extra.data] : []), ...(q.data?.items ?? [])]
    if (sev === 'all') return all
    if (sev === 'actionable') return all.filter((c) => c.analysis.severity !== 'low')
    return all.filter((c) => c.analysis.severity === sev)
  }, [q.data, extra.data, sev])
  const selectedId = Number(params.get('institution')) || items[0]?.institution.id
  const selected = [...(extra.data ? [extra.data] : []), ...(q.data?.items ?? [])].find((c) => c.institution.id === selectedId) ?? items[0]

  useEffect(() => {
    if (selected) document.getElementById(`ov-${selected.institution.id}`)?.scrollIntoView({ block: 'nearest' })
  }, [selected])

  if (q.isLoading) return <PageSkeleton />
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} />
  const s = q.data.summary
  const canAct = hasRole(['system_admin', 'senior_management', 'coordination_reviewer', 'bureau_officer'])

  return (
    <div>
      <PageHeader
        eyebrow={<span className="flex items-center gap-1.5"><Radar className="h-3.5 w-3.5" /> Overlap & Conflict Intelligence</span>}
        title="Overlap Radar"
        description="Institutions whose complaints are with more than one Bureau/Cell — classified as duplicate, conflicting, related or independent, with a proposed lead bureau."
        actions={
          <>
            <Segmented<Sev>
              value={sev}
              onChange={setSev}
              options={[
                { value: 'actionable', label: 'Needs action' },
                { value: 'critical', label: 'Critical' },
                { value: 'high', label: 'High' },
                { value: 'all', label: 'All' },
              ]}
            />
            {hasRole(['system_admin', 'senior_management', 'coordination_reviewer', 'data_admin']) && (
              <Button variant="secondary" size="md" loading={scan.isPending} onClick={() => scan.mutate()} leftIcon={<BellRing className="h-4 w-4" />}>
                Run alert scan
              </Button>
            )}
          </>
        }
      />

      <div className="stagger mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[
          { label: 'Institutions overlapping', value: s.institutions, tone: 'text-slate-900', icon: Building2 },
          { label: 'Critical', value: s.critical, tone: 'text-rose-600', icon: AlertOctagon },
          { label: 'High', value: s.high, tone: 'text-orange-600', icon: ShieldAlert },
          { label: 'Action conflicts', value: s.conflicts, tone: 'text-rose-600', icon: ArrowLeftRight },
          { label: 'Duplicates', value: s.duplicates, tone: 'text-violet-600', icon: Layers },
          { label: 'Awaiting coordination', value: s.awaiting_coordination, tone: 'text-gold-600', icon: GitMerge },
        ].map((m) => (
          <div key={m.label} className="card p-4">
            <div className="flex items-center justify-between">
              <p className="text-[11.5px] font-semibold text-slate-500">{m.label}</p>
              <m.icon className={cn('h-4 w-4', m.tone)} />
            </div>
            <p className={cn('mt-2 text-2xl font-extrabold', m.tone)}><AnimatedNumber value={m.value} /></p>
          </div>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="card"><EmptyState icon={Radar} title="Nothing on the radar" description="No institution matches this filter." /></div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[380px_1fr] [&>*]:min-w-0">
          <div className="space-y-2.5 xl:sticky xl:top-24 xl:max-h-[calc(100vh-7rem)] xl:overflow-y-auto xl:pr-1">
            {(q.data.total ?? 0) > (q.data.items?.length ?? 0) && (
              <p className="px-1 text-[11.5px] text-slate-500">Showing the {q.data.items.length} most severe of {q.data.total} institutions. Open any institution from search to see its analysis.</p>
            )}
            {items.map((c) => {
              const on = selected?.institution.id === c.institution.id
              const counts = c.analysis.classification_counts
              return (
                <button
                  id={`ov-${c.institution.id}`}
                  key={c.institution.id}
                  onClick={() => setParams({ institution: String(c.institution.id) })}
                  className={cn(
                    'relative w-full overflow-hidden rounded-2xl border bg-white p-4 pl-5 text-left transition-all duration-200',
                    on ? 'border-royal-300 shadow-glow' : 'border-slate-200/80 shadow-soft hover:border-slate-300 hover:shadow-card',
                  )}
                >
                  <span className={cn('absolute inset-y-0 left-0 w-1.5 bg-gradient-to-b', SEV_BAR[c.analysis.severity])} />
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-slate-900">{c.institution.short_name ?? c.institution.canonical_name}</p>
                      <p className="truncate text-xs text-slate-500">{c.institution.canonical_name}</p>
                    </div>
                    <SeverityBadge severity={c.analysis.severity} />
                  </div>
                  <p className="mt-2 line-clamp-1 text-[12.5px] font-medium text-slate-700">
                    {c.analysis.pairs.find((p) => p.classification !== 'independent')?.headline ?? 'Multiple bureaus, different issues'}
                  </p>
                  <div className="mt-3 flex flex-wrap items-center gap-1">
                    {c.analysis.active_bureaus.map((b) => <BureauChip key={b} code={b} />)}
                    <span className="ml-auto flex gap-1">
                      {Object.entries(counts).filter(([k]) => k !== 'independent').map(([k, v]) => (
                        <span key={k} title={CLASSIFICATION_META[k]?.label} className={cn('chip', CLASSIFICATION_META[k]?.chip)}>{v}</span>
                      ))}
                    </span>
                  </div>
                  {c.coordination && (
                    <p className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3 w-3" /> {c.coordination.reference_number} · coordinated
                    </p>
                  )}
                </button>
              )
            })}
            <p className="px-1 pt-1 text-[11px] text-slate-400">Updated {fromNow(q.data.generated_at)} · {fmtDate(q.data.generated_at, 'HH:mm')}</p>
          </div>
          <div className="min-w-0">{selected && <ClusterDetail cluster={selected} canAct={canAct} />}</div>
        </div>
      )}
      <div className="mt-8"><DataNote /></div>
    </div>
  )
}
