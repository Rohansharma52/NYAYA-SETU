import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeftRight, Check, ClipboardCheck, ShieldAlert, X } from 'lucide-react'
import { listRelationships, reviewRelationship } from '../../api/relationships'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, ClassificationBadge, EmptyState, ErrorState, Modal, Segmented, SeverityBadge, StatusBadge, TableSkeleton, Textarea } from '../../components/ui'
import { useAuth } from '../../contexts/AuthContext'
import { toast } from '../../hooks/useToast'
import { fromNow, titleCase } from '../../lib/format'
import type { CaseRelationship, RuleHit } from '../../types'

const TYPE_TO_CLASS: Record<string, string> = {
  possible_duplicate: 'duplicate', action_conflict: 'action_conflict', related_complaint: 'related_pattern', same_institution_unrelated: 'independent',
}

export default function RelationshipInboxPage() {
  const qc = useQueryClient()
  const { hasRole } = useAuth()
  const [status, setStatus] = useState<'pending' | 'confirmed' | 'rejected' | ''>('pending')
  const [target, setTarget] = useState<{ r: CaseRelationship; decision: 'confirmed' | 'rejected' } | null>(null)
  const [why, setWhy] = useState('')
  const q = useQuery({ queryKey: ['relationships', status], queryFn: () => listRelationships({ review_status: status || undefined, limit: 100 }) })
  const m = useMutation({
    mutationFn: () => reviewRelationship(target!.r.id, { decision: target!.decision, rationale: why }),
    onSuccess: () => { toast.success('Review recorded — source cases unchanged'); setTarget(null); setWhy(''); qc.invalidateQueries({ queryKey: ['relationships'] }) },
    onError: (e) => toast.error(apiError(e)),
  })
  const canReview = hasRole(['coordination_reviewer', 'system_admin', 'senior_management'])
  return (
    <div>
      <PageHeader eyebrow="Human-in-the-loop" title="Review Inbox"
        description="Suggested links between cases. A reviewer confirms or rejects each one with a reason; nothing is merged or closed automatically."
        actions={<Segmented value={status} onChange={setStatus} options={[{ value: 'pending', label: 'Pending' }, { value: 'confirmed', label: 'Confirmed' }, { value: 'rejected', label: 'Rejected' }, { value: '', label: 'All' }]} />} />
      <Card noPadding>
        {q.isLoading ? <TableSkeleton /> : q.isError ? <ErrorState onRetry={() => q.refetch()} /> : (q.data?.items ?? []).length === 0 ? (
          <EmptyState icon={ClipboardCheck} title="Inbox zero" description="No suggestions in this view." />
        ) : (
          <ul className="divide-y divide-slate-100">
            {q.data!.items.map((r) => {
              const ev = (r.matching_evidence ?? {}) as { severity?: string; rules?: RuleHit[]; classification?: string }
              return (
                <li key={r.id} className="p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <ClassificationBadge value={ev.classification ?? TYPE_TO_CLASS[r.relationship_type] ?? r.relationship_type} />
                    {ev.severity && <SeverityBadge severity={ev.severity} />}
                    <span className="text-xs text-slate-400">score {Math.round((r.score ?? 0) * 100)} · {r.algorithm_version} · {fromNow(r.created_at)}</span>
                    {r.review_status !== 'pending' && <span className="chip ml-auto border-slate-200 bg-slate-50 text-slate-600">{titleCase(r.review_status)}</span>}
                  </div>
                  <div className="mt-3 grid items-center gap-2 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
                    {[r.case_a, r.case_b].map((c, i) => c && (
                      <Link key={c.id} to={`/cases/${c.id}`} className={`min-w-0 rounded-xl border border-slate-200 p-3 transition hover:border-royal-200 ${i ? 'md:order-3' : ''}`}>
                        <div className="flex items-center justify-between gap-2"><span className="font-mono text-[11px] text-slate-400">{c.case_number}</span><StatusBadge status={c.status} /></div>
                        <p className="mt-1 truncate text-sm font-semibold text-slate-800">{c.title}</p>
                        <p className="text-xs text-slate-400">{c.category}</p>
                      </Link>
                    ))}
                    <span className="flex justify-center md:order-2"><ArrowLeftRight className="h-4 w-4 text-slate-400" /></span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1.5">{(r.reasons ?? []).map((x) => <span key={x} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{x}</span>)}</div>
                  {(ev.rules ?? []).map((rule) => (
                    <p key={rule.code} className="mt-2 flex gap-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-800"><ShieldAlert className="h-3.5 w-3.5 shrink-0" /><b>{rule.code}</b> {rule.explanation}</p>
                  ))}
                  {r.review_status === 'pending' && canReview && (
                    <div className="mt-3 flex justify-end gap-2">
                      <Button size="sm" variant="secondary" leftIcon={<X className="h-3.5 w-3.5" />} onClick={() => setTarget({ r, decision: 'rejected' })}>Not related</Button>
                      <Button size="sm" variant="success" leftIcon={<Check className="h-3.5 w-3.5" />} onClick={() => setTarget({ r, decision: 'confirmed' })}>Confirm link</Button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Card>
      <Modal isOpen={!!target} onClose={() => setTarget(null)} title={target?.decision === 'confirmed' ? 'Confirm link' : 'Reject suggestion'} description="Your rationale is stored with the review and audit log."
        footer={<><Button variant="secondary" onClick={() => setTarget(null)}>Cancel</Button><Button disabled={!why.trim()} loading={m.isPending} onClick={() => m.mutate()}>Submit</Button></>}>
        <Textarea label="Rationale" required rows={3} value={why} onChange={(e) => setWhy(e.target.value)} />
      </Modal>
    </div>
  )
}
