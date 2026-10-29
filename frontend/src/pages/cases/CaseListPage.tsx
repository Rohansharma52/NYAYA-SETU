import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download, FilePlus2, Filter, FolderKanban, RotateCcw } from 'lucide-react'
import { listCases } from '../../api/cases'
import { exportErrorMessage, saveExport } from '../../api/reports'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  BureauChip, Button, ButtonLink, Card, DataNote, EmptyState, ErrorState, Input, Pagination, PriorityBadge, SearchBar,
  Select, StatusBadge, Table, TableSkeleton, Tooltip,
} from '../../components/ui'
import type { TableColumn } from '../../components/ui'
import { useBureaus, useDebounce } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { CATEGORIES, REGIONS, STATUS_META, STATUS_OPTIONS } from '../../lib/domain'
import { daysUntil, fmtDate, fromNow } from '../../lib/format'
import { cn } from '../../lib/cn'
import type { Case } from '../../types'

const GROUPS: Record<string, string> = {
  pending: 'received,triaged,assigned,awaiting_information,reopened',
  under_process: 'under_process,decision_review',
  disposed: 'disposed,closed',
  transferred: 'transfer_requested,transferred',
}

const QUICK = [
  { id: '', label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'under_process', label: 'Under process' },
  { id: 'escalated', label: 'Escalated' },
  { id: 'transferred', label: 'Transferred' },
  { id: 'disposed', label: 'Disposed' },
  { id: 'overdue', label: 'Beyond timeline' },
]

const LIMIT = 25

export default function CaseListPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { bureaus } = useBureaus()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const [showFilters, setShowFilters] = useState(false)
  const dSearch = useDebounce(search, 300)
  const skip = Number(params.get('skip') ?? 0)

  const quick = params.get('overdue') ? 'overdue' : params.get('status') === 'escalated' ? 'escalated' : params.get('group') ?? ''
  const filters = {
    status: params.get('status') && params.get('status') !== 'escalated' ? params.get('status')! : undefined,
    bureau_id: params.get('bureau_id') ? Number(params.get('bureau_id')) : undefined,
    category: params.get('category') ?? undefined,
    region: params.get('region') ?? undefined,
    priority: params.get('priority') ?? undefined,
    aicte_id: params.get('aicte_id') ?? undefined,
    date_from: params.get('date_from') ?? undefined,
    date_to: params.get('date_to') ?? undefined,
  }
  const queryParams = {
    ...filters,
    search: dSearch || undefined,
    statuses: quick && GROUPS[quick] ? GROUPS[quick] : quick === 'escalated' ? 'escalated' : undefined,
    overdue: quick === 'overdue' ? true : undefined,
    skip,
    limit: LIMIT,
  }
  const q = useQuery({ queryKey: ['cases', queryParams], queryFn: () => listCases(queryParams), placeholderData: keepPreviousData })

  function set(key: string, value?: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('skip')
    setParams(next)
  }
  function setQuick(id: string) {
    const next = new URLSearchParams(params)
    ;['group', 'overdue', 'status', 'skip'].forEach((k) => next.delete(k))
    if (id === 'overdue') next.set('overdue', '1')
    else if (id === 'escalated') next.set('status', 'escalated')
    else if (id) next.set('group', id)
    setParams(next)
  }
  const activeFilters = Object.values(filters).filter(Boolean).length

  async function exportFile(kind: 'csv' | 'pdf') {
    try {
      // Export exactly what is on screen: same filters and quick-filter group
      const p = {
        status: queryParams.statuses ?? filters.status, bureau_id: filters.bureau_id, region: filters.region,
        category: filters.category, priority: filters.priority, overdue: queryParams.overdue,
      }
      const name = await saveExport(`/reports/cases/${kind}`, p, `nyaya-setu-cases.${kind}`)
      toast.success(`Downloaded ${name}`)
    } catch (e) {
      toast.error(await exportErrorMessage(e))
    }
  }

  const columns: TableColumn<Case>[] = useMemo(() => [
    {
      key: 'case', header: 'Case',
      render: (c) => (
        <div className="min-w-[220px] max-w-[300px]">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-medium text-slate-400">{c.case_number}</span>
            {!!c.overlap_bureaus?.length && (
              <Tooltip content={`Also open with ${c.overlap_bureaus.join(', ')} — coordination may be required`}>
                <span className="chip border-rose-200 bg-rose-50 text-rose-600"><AlertTriangle className="h-3 w-3" />Overlap · {c.overlap_bureaus.join(', ')}</span>
              </Tooltip>
            )}
          </div>
          <p className="mt-0.5 truncate font-semibold text-slate-800">{c.title}</p>
          <p className="truncate text-xs text-slate-400">{c.category}{c.source_case_id ? ` · ${c.source_case_id}` : ''}</p>
        </div>
      ),
    },
    {
      key: 'inst', header: 'Institution',
      render: (c) => <p className="max-w-[170px] truncate text-[13px] text-slate-600" title={c.institution?.canonical_name}>{c.institution?.canonical_name}</p>,
    },
    { key: 'bureau', header: 'Bureau / Cell', render: (c) => <BureauChip code={c.bureau?.code} /> },
    { key: 'status', header: 'Status', render: (c) => <StatusBadge status={c.status} /> },
    { key: 'priority', header: 'Priority', render: (c) => <PriorityBadge priority={c.priority} /> },
    {
      key: 'officer', header: 'Officer / last action',
      render: (c) => (
        <div className="max-w-[170px]">
          <p className="truncate text-[13px] font-medium text-slate-700">{c.assigned_officer?.full_name ?? <span className="text-slate-400">Unassigned</span>}</p>
          <p className="truncate text-xs text-slate-400" title={c.last_action ?? ''}>{c.last_action ? `${fromNow(c.last_action_date)} · ${c.last_action}` : '—'}</p>
        </div>
      ),
    },
    {
      key: 'due', header: 'Received → expected disposal',
      render: (c) => {
        const d = daysUntil(c.due_date)
        const open = !['disposed', 'closed', 'transferred'].includes(c.status)
        return (
          <div className="whitespace-nowrap text-[12.5px] text-slate-500">
            <p>{fmtDate(c.received_date, 'dd MMM')} → {fmtDate(c.due_date, 'dd MMM yy')}</p>
            {d !== null && open && (
              <p className={cn('text-[11px] font-semibold', d < 0 ? 'text-rose-600' : d <= 7 ? 'text-amber-600' : 'text-slate-400')}>
                {d < 0 ? `${-d} days overdue` : `${d} days left`}
              </p>
            )}
          </div>
        )
      },
    },
  ], [])

  return (
    <div>
      <PageHeader
        eyebrow="Complaint / case tracking"
        title="All Cases"
        description="Every institution-related complaint across RB, PGRC and other Bureaus/Cells — with the handling bureau, officer, last action and timeline."
        actions={
          <>
            <Button variant="secondary" leftIcon={<Download className="h-4 w-4" />} onClick={() => exportFile('csv')}>CSV</Button>
            <Button variant="secondary" leftIcon={<Download className="h-4 w-4" />} onClick={() => exportFile('pdf')}>PDF</Button>
            <ButtonLink to="/cases/new" leftIcon={<FilePlus2 className="h-4 w-4" />}>Register complaint</ButtonLink>
          </>
        }
      />

      <Card noPadding>
        <div className="space-y-4 border-b border-slate-100 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            <SearchBar value={search} onChange={(v) => { setSearch(v); set('q', v || undefined) }} placeholder="Search case ID, title, institution name, CPGRAMS / e-Office reference…" className="flex-1" />
            <Button variant={showFilters || activeFilters ? 'dark' : 'secondary'} leftIcon={<Filter className="h-4 w-4" />} onClick={() => setShowFilters((s) => !s)}>
              Filters{activeFilters ? ` · ${activeFilters}` : ''}
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {QUICK.map((t) => (
              <button
                key={t.id}
                onClick={() => setQuick(t.id)}
                className={cn('rounded-full px-3 py-1 text-xs font-semibold transition', quick === t.id ? 'bg-ink-900 text-white shadow-soft' : 'bg-slate-100 text-slate-600 hover:bg-slate-200')}
              >
                {t.label}
              </button>
            ))}
          </div>
          {showFilters && (
            <div className="grid animate-fade-in gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-2 lg:grid-cols-4">
              <Select label="Bureau / Cell" value={filters.bureau_id ?? ''} onChange={(e) => set('bureau_id', e.target.value)} placeholder="All" options={bureaus.map((b) => ({ value: String(b.id), label: `${b.code} — ${b.name}` }))} />
              <Select label="Status" value={filters.status ?? ''} onChange={(e) => set('status', e.target.value)} placeholder="Any" options={STATUS_OPTIONS} />
              <Select label="Category" value={filters.category ?? ''} onChange={(e) => set('category', e.target.value)} placeholder="Any" options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
              <Select label="Region" value={filters.region ?? ''} onChange={(e) => set('region', e.target.value)} placeholder="All regions" options={REGIONS.map((r) => ({ value: r, label: r }))} />
              <Select label="Priority" value={filters.priority ?? ''} onChange={(e) => set('priority', e.target.value)} placeholder="Any" options={['low', 'medium', 'high', 'urgent'].map((p) => ({ value: p, label: p[0].toUpperCase() + p.slice(1) }))} />
              <Input label="AICTE Permanent ID" value={filters.aicte_id ?? ''} onChange={(e) => set('aicte_id', e.target.value)} placeholder="1-28475…" />
              <Input label="Received from" type="date" value={filters.date_from ?? ''} onChange={(e) => set('date_from', e.target.value)} />
              <Input label="Received to" type="date" value={filters.date_to ?? ''} onChange={(e) => set('date_to', e.target.value)} />
              <div className="flex items-end sm:col-span-2 lg:col-span-4">
                <Button variant="ghost" size="sm" leftIcon={<RotateCcw className="h-3.5 w-3.5" />} onClick={() => { setSearch(''); setParams({}) }}>Reset all filters</Button>
              </div>
            </div>
          )}
        </div>

        {q.isLoading ? (
          <TableSkeleton rows={8} cols={6} />
        ) : q.isError ? (
          <ErrorState onRetry={() => q.refetch()} />
        ) : (
          <>
            <Table
              columns={columns}
              data={q.data?.items ?? []}
              rowKey={(c) => c.id}
              onRowClick={(c) => navigate(`/cases/${c.id}`)}
              rowClassName={(c) => (c.status === 'escalated' ? 'bg-rose-50/30' : undefined)}
              empty={<EmptyState icon={FolderKanban} title="No cases match" description="Try a different search or clear filters." />}
            />
            <div className="border-t border-slate-100 px-4 py-3">
              <Pagination total={q.data?.total ?? 0} skip={skip} limit={LIMIT} onPageChange={(s) => { const n = new URLSearchParams(params); n.set('skip', String(s)); setParams(n) }} />
            </div>
          </>
        )}
      </Card>
      <div className="mt-4 flex items-center justify-between">
        <DataNote />
        <p className="text-[11px] text-slate-400">{Object.keys(STATUS_META).length}-stage lifecycle · overlap flags computed live</p>
      </div>
    </div>
  )
}
