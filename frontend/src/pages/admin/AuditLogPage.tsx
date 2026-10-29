import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { ScrollText } from 'lucide-react'
import { listAudit, type AuditEvent } from '../../api/audit'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card, EmptyState, Pagination, SearchBar, Table, TableSkeleton } from '../../components/ui'
import { useDebounce } from '../../hooks/useData'
import { fmtDateTime, titleCase } from '../../lib/format'

export default function AuditLogPage() {
  const [action, setAction] = useState('')
  const [skip, setSkip] = useState(0)
  const da = useDebounce(action, 300)
  const q = useQuery({ queryKey: ['audit', da, skip], queryFn: () => listAudit({ action: da || undefined, skip, limit: 50 }), placeholderData: keepPreviousData })
  return (
    <div>
      <PageHeader eyebrow="Accountability & transparency" title="Audit trail" description="Every mutation, review, export and download — who, what and when. Append-only." />
      <Card noPadding>
        <div className="border-b border-slate-100 p-4"><SearchBar value={action} onChange={(v) => { setAction(v); setSkip(0) }} placeholder="Filter by action, e.g. status_changed, transfer, coordination…" /></div>
        {q.isLoading ? <TableSkeleton /> : (
          <>
            <Table<AuditEvent> data={q.data?.items ?? []} rowKey={(e) => e.id} empty={<EmptyState icon={ScrollText} title="No events" />} columns={[
              { key: 't', header: 'When', render: (e) => <span className="whitespace-nowrap text-xs text-slate-500">{fmtDateTime(e.created_at)}</span> },
              { key: 'u', header: 'User', render: (e) => <span className="text-[13px] font-medium">{e.user_name ?? (e.user_id ? `#${e.user_id}` : 'system')}</span> },
              { key: 'a', header: 'Action', render: (e) => <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-700">{e.action}</span> },
              { key: 'r', header: 'Resource', render: (e) => <span className="text-xs text-slate-500">{titleCase(e.resource_type)} {e.resource_id ? `#${e.resource_id}` : ''}</span> },
              { key: 'd', header: 'Details', render: (e) => <span className="line-clamp-1 max-w-[420px] text-[13px] text-slate-600">{e.description}</span> },
            ]} />
            <div className="border-t border-slate-100 px-4 py-3"><Pagination total={q.data?.total ?? 0} skip={skip} limit={50} onPageChange={setSkip} /></div>
          </>
        )}
      </Card>
    </div>
  )
}
