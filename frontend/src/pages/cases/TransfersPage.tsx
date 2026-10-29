import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, ArrowRight, Check, X } from 'lucide-react'
import { listTransfers, respondTransfer, type TransferRecord } from '../../api/cases'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { BureauChip, Button, Card, EmptyState, ErrorState, Modal, Segmented, TableSkeleton, Textarea } from '../../components/ui'
import { useAuth } from '../../contexts/AuthContext'
import { toast } from '../../hooks/useToast'
import { fmtDateTime, fromNow, titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'

export default function TransfersPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [status, setStatus] = useState<'requested' | 'accepted' | 'rejected' | ''>('requested')
  const [decide, setDecide] = useState<{ t: TransferRecord; accept: boolean } | null>(null)
  const [notes, setNotes] = useState('')
  const q = useQuery({ queryKey: ['transfers', status], queryFn: () => listTransfers(status) })
  const m = useMutation({
    mutationFn: () => respondTransfer(decide!.t.id, { accept: decide!.accept, notes: notes || undefined }),
    onSuccess: (r) => {
      toast.success(r.message)
      setDecide(null)
      setNotes('')
      qc.invalidateQueries({ queryKey: ['transfers'] })
    },
    onError: (e) => toast.error(apiError(e)),
  })
  const canRespond = (t: TransferRecord) =>
    ['system_admin', 'senior_management'].includes(user?.role as string) || (user?.role === 'bureau_officer' && user.bureau_id === t.to_bureau_id)

  return (
    <div>
      <PageHeader
        eyebrow="Movement of complaints"
        title="Transfers"
        description="Transfer requests between Bureaus/Cells. The receiving bureau accepts or rejects with reasons; every decision is recorded in the case history."
        actions={<Segmented value={status} onChange={setStatus} options={[{ value: 'requested', label: 'Pending' }, { value: 'accepted', label: 'Accepted' }, { value: 'rejected', label: 'Rejected' }, { value: '', label: 'All' }]} />}
      />
      <Card noPadding>
        {q.isLoading ? <TableSkeleton /> : q.isError ? <ErrorState onRetry={() => q.refetch()} /> : (q.data?.items ?? []).length === 0 ? (
          <EmptyState icon={ArrowLeftRight} title="No transfer requests" description="Nothing in this view." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {q.data!.items.map((t, i) => (
              <li key={t.id} className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center" style={{ animation: `fade-up .45s var(--ease-out) ${i * 0.04}s both` }}>
                <div className="flex items-center gap-2">
                  <BureauChip code={t.from_bureau} solid />
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-100"><ArrowRight className="h-3.5 w-3.5 text-slate-500" /></span>
                  <BureauChip code={t.to_bureau} solid />
                </div>
                <div className="min-w-0 flex-1">
                  <Link to={`/cases/${t.case_id}`} className="font-mono text-xs text-royal-600 hover:underline">{t.case_number}</Link>
                  <p className="truncate text-sm font-semibold text-slate-800">{t.case_title}</p>
                  <p className="text-xs text-slate-500">“{t.reason}” — {t.requested_by}, {fromNow(t.requested_at)}</p>
                  {t.response_notes && <p className="mt-1 text-xs text-slate-500">Response: {t.response_notes} ({t.responded_by}, {fmtDateTime(t.responded_at)})</p>}
                </div>
                {t.status === 'requested' && canRespond(t) ? (
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" leftIcon={<X className="h-3.5 w-3.5" />} onClick={() => setDecide({ t, accept: false })}>Reject</Button>
                    <Button variant="success" size="sm" leftIcon={<Check className="h-3.5 w-3.5" />} onClick={() => setDecide({ t, accept: true })}>Accept</Button>
                  </div>
                ) : (
                  <span className={cn('chip', t.status === 'accepted' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : t.status === 'rejected' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-cyan-200 bg-cyan-50 text-cyan-700')}>
                    {t.status === 'requested' ? `Awaiting ${t.to_bureau}` : titleCase(t.status)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Modal isOpen={!!decide} onClose={() => setDecide(null)} title={decide?.accept ? 'Accept transfer' : 'Reject transfer'}
        description={decide?.accept ? 'The case moves to your bureau and is marked Transferred.' : 'A reason is required; the case returns to the sending bureau.'}
        footer={<><Button variant="secondary" onClick={() => setDecide(null)}>Cancel</Button><Button variant={decide?.accept ? 'success' : 'danger'} loading={m.isPending} disabled={!decide?.accept && !notes.trim()} onClick={() => m.mutate()}>{decide?.accept ? 'Accept' : 'Reject'}</Button></>}>
        <Textarea label="Remarks" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </Modal>
    </div>
  )
}
