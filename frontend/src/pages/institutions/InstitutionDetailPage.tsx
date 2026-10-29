import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertOctagon, BadgeCheck, Building2, Download, FileText, Globe, Mail, MapPin, Phone, Radar, ShieldAlert, Tags } from 'lucide-react'
import { getInstitution360 } from '../../api/intelligence'
import { exportErrorMessage, saveExport } from '../../api/reports'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  BureauChip, Button, ButtonLink, Card, ClassificationBadge, DataNote, ErrorState, PageSkeleton, ScoreRing, SeverityBadge,
  StatusBadge, Table, Timeline, RiskBadge,
} from '../../components/ui'
import { toast } from '../../hooks/useToast'
import { bureauStyle, RISK_META } from '../../lib/domain'
import { daysUntil, fmtDate, titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'
import type { CaseBrief } from '../../types'

export default function InstitutionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const q = useQuery({ queryKey: ['i360', id], queryFn: () => getInstitution360(Number(id)) })
  if (q.isLoading) return <PageSkeleton />
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} />
  const { institution: inst, cases, by_bureau, overlap, risk, timeline } = q.data
  const total = cases.length
  const openCount = by_bureau.reduce((a, b) => a + b.open, 0)

  async function pdf() {
    try {
      const name = await saveExport(`/reports/institution/${inst.id}/pdf`, {}, `institution-${inst.short_name ?? inst.id}.pdf`)
      toast.success(`Downloaded ${name}`)
    } catch (e) {
      toast.error(await exportErrorMessage(e))
    }
  }

  return (
    <div>
      <PageHeader
        docTitle={inst.short_name ?? inst.canonical_name}
        breadcrumbs={[{ label: 'Institutions', href: '/institutions' }, { label: inst.short_name ?? inst.canonical_name }]}
        eyebrow="Institution 360°"
        title={inst.canonical_name}
        description={<span className="flex items-center gap-1.5"><MapPin className="h-3.5 w-3.5" />{[inst.address, inst.city, inst.state, inst.pincode].filter(Boolean).join(', ')} · {inst.region} region</span>}
        actions={<>
          <Button variant="secondary" leftIcon={<Download className="h-4 w-4" />} onClick={pdf}>Complaint history PDF</Button>
          <ButtonLink to={`/cases?q=${encodeURIComponent(inst.canonical_name)}`} variant="secondary" leftIcon={<FileText className="h-4 w-4" />}>All cases</ButtonLink>
        </>}
      />

      {overlap?.banner && (
        <button onClick={() => navigate(`/overlaps?institution=${inst.id}`)} className="mb-6 flex w-full items-center gap-3 rounded-2xl border border-rose-200 bg-gradient-to-r from-rose-50 to-white p-4 text-left transition hover:shadow-card">
          <AlertOctagon className="h-5 w-5 text-rose-600" />
          <span className="flex-1">
            <span className="block text-sm font-bold text-rose-800">{overlap.banner}</span>
            <span className="text-[13px] text-rose-700/80">{overlap.active_bureaus.join(', ')} are handling related files · lead proposed: {overlap.lead_bureau?.bureau_code ?? '—'}</span>
          </span>
          <SeverityBadge severity={overlap.severity} />
          <Radar className="h-4 w-4 text-rose-400" />
        </button>
      )}

      <div className="grid gap-6 xl:grid-cols-3">
        {/* Profile */}
        <Card title="Profile & identifiers" icon={<Building2 className="h-5 w-5" />}>
          <dl className="space-y-3 text-sm">
            {inst.identifiers.filter((x) => x.id_type !== 'hindi_name').map((x) => (
              <div key={x.id_type + x.id_value} className="flex items-center justify-between gap-3">
                <dt className="text-slate-500">{titleCase(x.id_type.replace('aicte_permanent_id', 'AICTE Permanent ID').replace('aishe_code', 'AISHE code'))}</dt>
                <dd className="flex items-center gap-1 font-mono text-[13px] font-semibold text-slate-800">{x.id_value}{x.is_verified && <BadgeCheck className="h-3.5 w-3.5 text-emerald-500" />}</dd>
              </div>
            ))}
            <div className="flex justify-between"><dt className="text-slate-500">Type</dt><dd className="font-medium">{inst.institution_type}</dd></div>
            {inst.email && <div className="flex items-center gap-2 text-slate-600"><Mail className="h-3.5 w-3.5" />{inst.email}</div>}
            {inst.phone && <div className="flex items-center gap-2 text-slate-600"><Phone className="h-3.5 w-3.5" />{inst.phone}</div>}
            {inst.website && <div className="flex items-center gap-2 text-slate-600"><Globe className="h-3.5 w-3.5" />{inst.website}</div>}
          </dl>
          {inst.known_aliases.length > 0 && (
            <div className="mt-4 border-t border-slate-100 pt-4">
              <p className="flex items-center gap-1.5 text-xs font-bold text-slate-700"><Tags className="h-3.5 w-3.5" />Known name variants (used by identity resolution)</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {inst.known_aliases.map((a) => <span key={a} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{a}</span>)}
              </div>
            </div>
          )}
        </Card>

        {/* Bureau split */}
        <Card title="Who is handling this institution" subtitle={`${total} complaints · ${openCount} open`}>
          <div className="space-y-3">
            {by_bureau.map((b) => {
              const st = bureauStyle(b.bureau_code)
              return (
                <div key={b.bureau_code} className="flex items-center gap-3">
                  <BureauChip code={b.bureau_code} />
                  <div className="flex-1">
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full" style={{ width: `${(b.total / Math.max(total, 1)) * 100}%`, background: st.color, transition: 'width 1s' }} />
                    </div>
                  </div>
                  <span className="w-24 text-right text-xs text-slate-500 tabular"><b className="text-slate-800">{b.open}</b> open / {b.total}</span>
                </div>
              )
            })}
          </div>
          {overlap && (
            <div className="mt-5 flex flex-wrap gap-1.5 border-t border-slate-100 pt-4">
              {Object.entries(overlap.classification_counts).map(([k, v]) => (
                <span key={k} className="flex items-center gap-1"><ClassificationBadge value={k} /><span className="text-xs font-bold text-slate-600">×{v}</span></span>
              ))}
            </div>
          )}
        </Card>

        {/* Risk */}
        <Card title="Risk radar" icon={<ShieldAlert className="h-5 w-5" />} action={<RiskBadge level={risk.level} />}>
          <div className="flex items-center gap-5">
            <ScoreRing value={risk.score} color={RISK_META[risk.level].color} size={96} sublabel="risk" />
            <div className="space-y-1 text-xs text-slate-500">
              <p><b className="text-slate-800">{risk.complaints_90d}</b> complaints in 90 days</p>
              <p><b className="text-slate-800">{risk.open_cases}</b> open · <b className={risk.overdue_cases ? 'text-rose-600' : 'text-slate-800'}>{risk.overdue_cases}</b> overdue</p>
              {risk.systemic_issues.map((s) => <p key={s.issue} className="font-semibold text-orange-600">Systemic: {s.label} ×{s.count}</p>)}
            </div>
          </div>
          <ul className="mt-4 space-y-1.5">
            {risk.factors.map((f) => (
              <li key={f.code} className="flex items-center gap-2 text-xs">
                <span className="w-10 text-right font-bold text-slate-700 tabular">+{f.points}</span>
                <span className="font-semibold text-slate-700">{f.label}</span>
                <span className="truncate text-slate-400">{f.detail}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-600">{risk.recommendations[0]}</div>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card title="Consolidated complaint history" subtitle="All Bureaus / Cells — single source of truth" noPadding>
          <Table<CaseBrief>
            data={cases}
            rowKey={(c) => c.id}
            onRowClick={(c) => navigate(`/cases/${c.id}`)}
            columns={[
              { key: 'c', header: 'Case', render: (c) => <div className="max-w-[260px]"><p className="font-mono text-[11px] text-slate-400">{c.case_number}</p><p className="truncate font-semibold text-slate-800">{c.title}</p></div> },
              { key: 'b', header: 'Bureau', render: (c) => <BureauChip code={c.bureau_code} /> },
              { key: 's', header: 'Status', render: (c) => <StatusBadge status={c.status} /> },
              { key: 'r', header: 'Received', render: (c) => <span className="whitespace-nowrap text-xs text-slate-500">{fmtDate(c.received_date)}</span> },
              {
                key: 'd', header: 'Due', render: (c) => {
                  const d = daysUntil(c.due_date)
                  const open = !['disposed', 'closed', 'transferred'].includes(c.status)
                  return <span className={cn('whitespace-nowrap text-xs font-semibold', open && d !== null && d < 0 ? 'text-rose-600' : 'text-slate-500')}>{open && d !== null ? (d < 0 ? `${-d}d overdue` : `${d}d left`) : fmtDate(c.due_date)}</span>
                },
              },
            ]}
          />
        </Card>
        <Card title="Cross-bureau timeline" subtitle="Every action on this institution, newest first">
          <div className="max-h-[560px] overflow-y-auto pr-1">
            <Timeline compact events={timeline.slice(0, 30).map((t, i) => ({ id: `${t.case_id}-${i}`, type: t.action_type, description: t.description, performedBy: t.performed_by, createdAt: t.created_at, bureau: t.bureau_code, caseNumber: t.case_number }))} />
          </div>
        </Card>
      </div>
      <div className="mt-6"><DataNote /></div>
    </div>
  )
}
