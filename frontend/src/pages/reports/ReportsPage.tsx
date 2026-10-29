import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { BarChart3, Building2, Download, FileSpreadsheet, FileText, Layers, Map, Radar } from 'lucide-react'
import { getOverview, getPerformance, getRegions } from '../../api/analytics'
import { listOverlaps } from '../../api/intelligence'
import { exportErrorMessage, saveExport } from '../../api/reports'
import { PageHeader } from '../../components/layout/PageHeader'
import { BureauChip, Button, Card, DataNote, ErrorState, Meter, PageSkeleton, Segmented, SeverityBadge, StatusBadge, Tabs } from '../../components/ui'
import { toast } from '../../hooks/useToast'
import { bureauStyle, STATUS_META } from '../../lib/domain'
import { downloadCSV, pct } from '../../lib/format'
import { cn } from '../../lib/cn'

type Tab = 'performance' | 'bureau' | 'region' | 'status' | 'institution' | 'overlap'

function ExportBtn({ onClick, label = 'Export CSV' }: { onClick: () => void; label?: string }) {
  return <Button size="sm" variant="secondary" leftIcon={<Download className="h-3.5 w-3.5" />} onClick={onClick}>{label}</Button>
}

export default function ReportsPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('performance')
  const [period, setPeriod] = useState<'monthly' | 'quarterly'>('monthly')
  const perf = useQuery({ queryKey: ['performance', period], queryFn: () => getPerformance({ period, months: 12 }) })
  const ov = useQuery({ queryKey: ['overview', 'reports'], queryFn: () => getOverview() })
  const regions = useQuery({ queryKey: ['regions'], queryFn: getRegions })
  const overlaps = useQuery({ queryKey: ['overlaps', 'reports'], queryFn: () => listOverlaps({ limit: 1000 }), enabled: tab === 'overlap' })

  const [busy, setBusy] = useState<string | null>(null)
  async function serverExport(kind: 'csv' | 'pdf' | 'coord') {
    setBusy(kind)
    try {
      const path = kind === 'csv' ? '/reports/cases/csv' : kind === 'pdf' ? '/reports/cases/pdf' : '/reports/coordination/csv'
      const name = await saveExport(path, {}, `nyaya-setu-${kind}`)
      toast.success(`Downloaded ${name}`)
    } catch (e) {
      toast.error(await exportErrorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  if (perf.isLoading || ov.isLoading) return <PageSkeleton />
  if (perf.isError || ov.isError || !perf.data || !ov.data) return <ErrorState onRetry={() => { perf.refetch(); ov.refetch() }} />
  const p = perf.data
  const o = ov.data

  return (
    <div>
      <PageHeader
        eyebrow="Reports & analytics"
        title="Reports"
        description="Bureau-wise, region-wise, status-wise and institution-wise reports, pending-case ageing, disposal rate, overlap report and monthly / quarterly performance — computed live from the same records."
        actions={<>
          <Button variant="secondary" leftIcon={<FileSpreadsheet className="h-4 w-4" />} loading={busy === 'csv'} onClick={() => serverExport('csv')}>All cases CSV</Button>
          <Button variant="secondary" leftIcon={<FileText className="h-4 w-4" />} loading={busy === 'pdf'} onClick={() => serverExport('pdf')}>Case register PDF</Button>
          <Button variant="secondary" leftIcon={<Download className="h-4 w-4" />} loading={busy === 'coord'} onClick={() => serverExport('coord')}>Coordination CSV</Button>
        </>}
      />

      <div className="stagger mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          { l: 'Received (12 mo)', v: p.summary.received },
          { l: 'Disposed (12 mo)', v: p.summary.disposed },
          { l: 'Clearance rate', v: pct(p.summary.clearance_rate) },
          { l: 'Avg. days to dispose', v: o.avg_disposal_days ?? '—' },
        ].map((k) => (
          <div key={k.l} className="card p-4">
            <p className="text-xs font-semibold text-slate-500">{k.l}</p>
            <p className="mt-1 text-2xl font-extrabold text-slate-900 tabular">{k.v}</p>
          </div>
        ))}
      </div>

      <Tabs className="mb-5" activeTab={tab} onTabChange={(t) => setTab(t as Tab)} tabs={[
        { id: 'performance', label: 'Monthly / quarterly', icon: <BarChart3 className="h-4 w-4" /> },
        { id: 'bureau', label: 'Bureau-wise', icon: <Layers className="h-4 w-4" /> },
        { id: 'region', label: 'Region-wise', icon: <Map className="h-4 w-4" /> },
        { id: 'status', label: 'Status-wise' },
        { id: 'institution', label: 'Institution-wise', icon: <Building2 className="h-4 w-4" /> },
        { id: 'overlap', label: 'Overlap report', icon: <Radar className="h-4 w-4" /> },
      ]} />

      {tab === 'performance' && (
        <Card title="Performance report" subtitle={p.definitions.clearance_rate}
          action={<div className="flex gap-2"><Segmented value={period} onChange={setPeriod} options={[{ value: 'monthly', label: 'Monthly' }, { value: 'quarterly', label: 'Quarterly (FY)' }]} /><ExportBtn onClick={() => downloadCSV(`NYAYA_SETU_Performance_${period}.csv`, p.rows as unknown as Record<string, unknown>[], [{ key: 'label', label: 'Period' }, { key: 'received', label: 'Received' }, { key: 'disposed', label: 'Disposed' }, { key: 'clearance_rate', label: 'Clearance %' }, { key: 'avg_disposal_days', label: 'Avg. days to dispose' }, { key: 'on_time_rate', label: 'Disposed on time %' }, { key: 'pending_end', label: 'Pending at period end' }])} /></div>}>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={p.rows} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid stroke="#EEF1F7" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                <YAxis yAxisId="l" allowDecimals={false} tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                <YAxis yAxisId="r" orientation="right" domain={[0, 'auto']} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: '#94A3B8' }} tickLine={false} axisLine={false} />
                <RTooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar yAxisId="l" dataKey="received" name="Received" fill="#A3AEFB" radius={[6, 6, 0, 0]} />
                <Bar yAxisId="l" dataKey="disposed" name="Disposed" fill="#10B981" radius={[6, 6, 0, 0]} />
                <Line yAxisId="r" type="monotone" dataKey="clearance_rate" name="Clearance %" stroke="#EC960B" strokeWidth={2.5} dot={{ r: 3 }} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-5 overflow-x-auto">
            <table className="table-modern w-full min-w-[720px]">
              <thead><tr><th>Period</th><th className="text-right">Received</th><th className="text-right">Disposed</th><th className="text-right">Clearance</th><th className="text-right">Avg. days</th><th className="text-right">On time</th><th className="text-right">Pending at end</th></tr></thead>
              <tbody>{p.rows.map((r) => (
                <tr key={r.period}>
                  <td className="font-semibold">{r.label}</td><td className="text-right tabular">{r.received}</td><td className="text-right tabular">{r.disposed}</td>
                  <td className={cn('text-right font-semibold tabular', (r.clearance_rate ?? 0) >= 100 ? 'text-emerald-600' : (r.clearance_rate ?? 0) < 60 ? 'text-rose-600' : 'text-slate-700')}>{pct(r.clearance_rate)}</td>
                  <td className="text-right tabular">{r.avg_disposal_days ?? '—'}</td><td className="text-right tabular">{pct(r.on_time_rate)}</td><td className="text-right tabular">{r.pending_end}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'bureau' && (
        <Card title="Bureau / Cell-wise report" action={<ExportBtn onClick={() => downloadCSV('NYAYA_SETU_Bureau_report.csv', o.bureau_workload as unknown as Record<string, unknown>[], [{ key: 'code', label: 'Bureau' }, { key: 'name', label: 'Bureau / Cell' }, { key: 'total', label: 'Total cases' }, { key: 'open', label: 'Open' }, { key: 'overdue', label: 'Beyond timeline' }, { key: 'disposed', label: 'Disposed' }, { key: 'escalated', label: 'Escalated' }, { key: 'disposal_rate', label: 'Disposal rate %' }])} />} noPadding>
          <div className="overflow-x-auto px-2 pb-2">
            <table className="table-modern w-full min-w-[760px]">
              <thead><tr><th>Bureau / Cell</th><th className="text-right">Total</th><th className="text-right">Open</th><th className="text-right">Overdue</th><th className="text-right">Escalated</th><th className="text-right">Disposed</th><th className="w-48">Disposal rate</th><th className="text-right">Clearance (12 mo)</th><th className="text-right">Avg. days</th></tr></thead>
              <tbody>{o.bureau_workload.map((b) => {
                const pb = p.by_bureau.find((x) => x.bureau_code === b.code)
                return (
                  <tr key={b.code}>
                    <td><div className="flex items-center gap-2"><BureauChip code={b.code} /><span className="text-xs text-slate-500">{b.name}</span></div></td>
                    <td className="text-right font-bold tabular">{b.total}</td><td className="text-right tabular">{b.open}</td>
                    <td className={cn('text-right tabular', b.overdue && 'font-bold text-rose-600')}>{b.overdue}</td><td className="text-right tabular">{b.escalated}</td><td className="text-right tabular">{b.disposed}</td>
                    <td><div className="flex items-center gap-2"><Meter value={b.disposal_rate} color={bureauStyle(b.code).color} /><span className="w-12 text-right text-xs font-semibold tabular">{pct(b.disposal_rate)}</span></div></td>
                    <td className="text-right tabular">{pct(pb?.clearance_rate)}</td><td className="text-right tabular">{pb?.avg_disposal_days ?? '—'}</td>
                  </tr>
                )
              })}</tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'region' && (
        <Card title="Region-wise report" subtitle="AICTE regional offices" action={<ExportBtn onClick={() => downloadCSV('NYAYA_SETU_Region_report.csv', (regions.data?.items ?? []) as unknown as Record<string, unknown>[], [{ key: 'region', label: 'Region' }, { key: 'institutions', label: 'Institutions' }, { key: 'total', label: 'Total cases' }, { key: 'open', label: 'Open' }, { key: 'overdue', label: 'Beyond timeline' }, { key: 'disposed', label: 'Disposed' }, { key: 'disposal_rate', label: 'Disposal rate %' }])} />}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {(regions.data?.items ?? []).map((r) => (
              <div key={r.region} className="rounded-2xl border border-slate-200 p-4">
                <div className="flex items-center justify-between"><p className="font-bold text-slate-900">{r.region}</p><span className="text-xs text-slate-400">{r.institutions} inst.</span></div>
                <p className="mt-2 text-2xl font-extrabold tabular">{r.total}<span className="text-sm font-medium text-slate-400"> cases</span></p>
                <div className="mt-2 flex gap-3 text-xs"><span><b>{r.open}</b> open</span><span className={r.overdue ? 'font-bold text-rose-600' : ''}>{r.overdue} overdue</span><span>{r.disposed} disposed</span></div>
                <Meter value={r.disposal_rate} className="mt-3" barClassName="from-emerald-500 to-emerald-400" />
                <p className="mt-1 text-right text-[11px] text-slate-400">{pct(r.disposal_rate)} disposal</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === 'status' && (
        <Card title="Status-wise report" action={<ExportBtn onClick={() => downloadCSV('NYAYA_SETU_Status_report.csv', Object.entries(o.by_status).map(([status, count]) => ({ status: STATUS_META[status]?.label ?? status, count })), [{ key: 'status', label: 'Status' }, { key: 'count', label: 'Cases' }])} />}>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(o.by_status).sort((a, b) => b[1] - a[1]).map(([s, n]) => (
              <button key={s} onClick={() => navigate(`/cases?status=${s}`)} className="flex items-center justify-between rounded-xl border border-slate-200 p-3 text-left transition hover:border-royal-200 hover:shadow-soft">
                <StatusBadge status={s} /><span className="text-lg font-extrabold tabular">{n}</span>
              </button>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-400">{Object.keys(STATUS_META).length} lifecycle statuses grouped on the dashboard as pending, under process, escalated, transferred and disposed.</p>
        </Card>
      )}

      {tab === 'institution' && (
        <Card title="Institution-wise complaint history" subtitle="Institutions with the most open cases — open any for the full 360° history" action={<ExportBtn onClick={() => downloadCSV('NYAYA_SETU_Institution_report.csv', o.institutions.map((r) => ({ ...r, bureaus: r.bureaus.join(', ') })), [{ key: 'name', label: 'Institution' }, { key: 'short_name', label: 'Short name' }, { key: 'region', label: 'Region' }, { key: 'total', label: 'Total cases' }, { key: 'open', label: 'Open' }, { key: 'overdue', label: 'Beyond timeline' }, { key: 'disposed', label: 'Disposed' }, { key: 'bureaus', label: 'Bureaus / Cells' }])} />} noPadding>
          <div className="overflow-x-auto px-2 pb-2">
            <table className="table-modern w-full min-w-[680px]">
              <thead><tr><th>Institution</th><th>Region</th><th>Bureaus</th><th className="text-right">Total</th><th className="text-right">Open</th><th className="text-right">Overdue</th><th className="text-right">Disposed</th></tr></thead>
              <tbody>{o.institutions.map((r) => (
                <tr key={r.institution_id} className="cursor-pointer" onClick={() => navigate(`/institutions/${r.institution_id}`)}>
                  <td className="font-semibold">{r.name}</td><td className="text-slate-500">{r.region}</td>
                  <td><div className="flex gap-1">{r.bureaus.map((b) => <BureauChip key={b} code={b} />)}</div></td>
                  <td className="text-right tabular">{r.total}</td><td className="text-right font-bold tabular">{r.open}</td>
                  <td className={cn('text-right tabular', r.overdue && 'font-bold text-rose-600')}>{r.overdue}</td><td className="text-right tabular">{r.disposed}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'overlap' && (
        <Card title="Overlapping / duplicate cases report" action={<ExportBtn onClick={() => downloadCSV('NYAYA_SETU_Overlap_report.csv', (overlaps.data?.items ?? []).map((c) => ({ institution: c.institution.canonical_name, severity: c.analysis.severity, bureaus: c.analysis.active_bureaus.join(', '), lead: c.analysis.lead_bureau?.bureau_code ?? '', duplicate: c.analysis.classification_counts.duplicate ?? 0, action_conflict: c.analysis.classification_counts.action_conflict ?? 0, related_pattern: c.analysis.classification_counts.related_pattern ?? 0, coordination: c.coordination?.reference_number ?? '' })), [{ key: 'institution', label: 'Institution' }, { key: 'severity', label: 'Severity' }, { key: 'bureaus', label: 'Bureaus with open files' }, { key: 'lead', label: 'Proposed lead bureau' }, { key: 'duplicate', label: 'Duplicates' }, { key: 'action_conflict', label: 'Action conflicts' }, { key: 'related_pattern', label: 'Related issues' }, { key: 'coordination', label: 'Coordination ref.' }])} />} noPadding>
          <div className="overflow-x-auto px-2 pb-2">
            <table className="table-modern w-full min-w-[760px]">
              <thead><tr><th>Institution</th><th>Severity</th><th>Bureaus</th><th className="text-right">Conflicts</th><th className="text-right">Duplicates</th><th className="text-right">Related</th><th>Lead</th><th>Coordination</th></tr></thead>
              <tbody>{(overlaps.data?.items ?? []).map((c) => (
                <tr key={c.institution.id} className="cursor-pointer" onClick={() => navigate(`/overlaps?institution=${c.institution.id}`)}>
                  <td className="font-semibold">{c.institution.canonical_name}</td><td><SeverityBadge severity={c.analysis.severity} /></td>
                  <td><div className="flex gap-1">{c.analysis.active_bureaus.map((b) => <BureauChip key={b} code={b} />)}</div></td>
                  <td className="text-right tabular">{c.analysis.classification_counts.action_conflict ?? 0}</td>
                  <td className="text-right tabular">{c.analysis.classification_counts.duplicate ?? 0}</td>
                  <td className="text-right tabular">{c.analysis.classification_counts.related_pattern ?? 0}</td>
                  <td>{c.analysis.lead_bureau ? <BureauChip code={c.analysis.lead_bureau.bureau_code} /> : '—'}</td>
                  <td className="text-xs font-semibold text-emerald-600">{c.coordination?.reference_number ?? <span className="text-slate-400">Not started</span>}</td>
                </tr>))}</tbody>
            </table>
          </div>
        </Card>
      )}
      <div className="mt-6"><DataNote /></div>
    </div>
  )
}
