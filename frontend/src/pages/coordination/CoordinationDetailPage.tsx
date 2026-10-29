import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Check, CheckCircle2, Circle, Crown, Gavel, Lock, Plus, ShieldCheck } from 'lucide-react'
import { acknowledge, addTask, closeCoordination, completeTask, getCoordination, recordDecision } from '../../api/coordination'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { BureauChip, Button, Card, ErrorState, Input, Modal, PageSkeleton, Select, Textarea } from '../../components/ui'
import { useAuth } from '../../contexts/AuthContext'
import { useBureaus } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { daysUntil, fmtDate, fmtDateTime } from '../../lib/format'
import { cn } from '../../lib/cn'
import { COORD_STATUS } from './shared'

const FLOW = ['detected', 'under_review', 'active', 'acknowledged', 'follow_up', 'closure_review', 'closed']

export default function CoordinationDetailPage() {
  const { id } = useParams()
  const cid = Number(id)
  const qc = useQueryClient()
  const { user, hasRole } = useAuth()
  const { byId } = useBureaus()
  const [taskTitle, setTaskTitle] = useState('')
  const [closeOpen, setCloseOpen] = useState(false)
  const [decisionOpen, setDecisionOpen] = useState(false)
  const [notes, setNotes] = useState('')
  const [exception, setException] = useState(false)
  const [decision, setDecision] = useState('coordinate')
  const q = useQuery({ queryKey: ['coordination', cid], queryFn: () => getCoordination(cid) })
  const refresh = (msg: string) => { toast.success(msg); qc.invalidateQueries({ queryKey: ['coordination'] }) }
  const fail = (e: unknown) => toast.error(apiError(e))
  const ackM = useMutation({ mutationFn: () => acknowledge(cid), onSuccess: () => refresh('Acknowledged on behalf of your bureau'), onError: fail })
  const taskM = useMutation({ mutationFn: () => addTask(cid, { title: taskTitle }), onSuccess: () => { setTaskTitle(''); refresh('Task added') }, onError: fail })
  const doneM = useMutation({ mutationFn: (tid: number) => completeTask(cid, tid), onSuccess: () => refresh('Task completed'), onError: fail })
  const closeM = useMutation({ mutationFn: () => closeCoordination(cid, { closure_notes: notes, is_exception: exception, exception_reason: exception ? notes : undefined }), onSuccess: () => { setCloseOpen(false); refresh('Coordination closed') }, onError: fail })
  const decM = useMutation({ mutationFn: () => recordDecision(cid, { decision, rationale: notes }), onSuccess: () => { setDecisionOpen(false); refresh('Decision recorded') }, onError: fail })

  if (q.isLoading) return <PageSkeleton />
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} />
  const c = q.data
  const st = COORD_STATUS[c.status] ?? COORD_STATUS.detected
  const closed = ['closed', 'dismissed'].includes(c.status)
  const idx = FLOW.indexOf(c.status)
  const lead = c.lead_bureau_id ? byId.get(c.lead_bureau_id) : undefined
  const myPart = c.participants.find((p) => p.user_id === user?.id || (p.bureau_id && p.bureau_id === user?.bureau_id))
  const due = daysUntil(c.action_due_date)
  const pendingAcks = c.participants.filter((p) => !p.acknowledged).length
  const openTasks = c.tasks.filter((t) => !t.is_completed).length

  return (
    <div>
      <PageHeader
        docTitle={c.reference_number}
        breadcrumbs={[{ label: 'Coordination', href: '/coordination' }, { label: c.reference_number }]}
        eyebrow={<span className="font-mono normal-case tracking-normal">{c.reference_number}</span>}
        title={c.title}
        description={<span className="flex flex-wrap items-center gap-2"><span className={cn('chip', st.chip)}>{st.label}</span>{c.institution_id && <Link className="inline-flex items-center gap-1 font-semibold text-royal-600 hover:underline" to={`/institutions/${c.institution_id}`}><Building2 className="h-3.5 w-3.5" />Institution 360°</Link>}</span>}
        actions={!closed && <>
          {myPart && !myPart.acknowledged && <Button variant="success" leftIcon={<Check className="h-4 w-4" />} loading={ackM.isPending} onClick={() => ackM.mutate()}>Acknowledge</Button>}
          {hasRole(['coordination_reviewer', 'system_admin', 'senior_management']) && <Button variant="secondary" leftIcon={<Gavel className="h-4 w-4" />} onClick={() => setDecisionOpen(true)}>Record decision</Button>}
          {hasRole(['coordination_reviewer', 'system_admin']) && <Button variant="dark" leftIcon={<Lock className="h-4 w-4" />} onClick={() => setCloseOpen(true)}>Close</Button>}
        </>}
      />

      <div className="card mb-6 overflow-x-auto p-5">
        <ol className="flex min-w-[720px] items-center">
          {FLOW.map((s, i) => (
            <li key={s} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1.5">
                <span className={cn('flex h-8 w-8 items-center justify-center rounded-full border-2 text-[11px] font-bold',
                  i < idx || c.status === 'closed' ? 'border-emerald-500 bg-emerald-500 text-white' : i === idx ? 'border-royal-500 bg-royal-500 text-white shadow-[0_0_0_6px_rgba(91,102,236,.15)]' : 'border-slate-200 text-slate-400')}>
                  {i < idx || c.status === 'closed' ? <Check className="h-4 w-4" /> : i + 1}
                </span>
                <span className={cn('whitespace-nowrap text-[11px] font-semibold', i === idx ? 'text-slate-900' : 'text-slate-400')}>{COORD_STATUS[s].label}</span>
              </div>
              {i < FLOW.length - 1 && <span className={cn('mx-2 mb-5 h-0.5 flex-1 rounded-full', i < idx ? 'bg-emerald-400' : 'bg-slate-200')} />}
            </li>
          ))}
        </ol>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_1fr] [&>*]:min-w-0">
        <div className="space-y-6">
          {c.description && (
            <Card title="Context">
              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">{c.description}</p>
              {c.decision_rationale && <p className="mt-4 rounded-xl bg-gold-50 p-3 text-[13px] text-gold-900"><b>Decision rationale:</b> {c.decision_rationale}</p>}
            </Card>
          )}
          <Card title="Follow-up tasks" subtitle={`${c.tasks.filter((t) => t.is_completed).length} of ${c.tasks.length} complete`} icon={<ShieldCheck className="h-5 w-5" />}>
            <ul className="space-y-2">
              {c.tasks.map((t) => {
                const d = daysUntil(t.due_date)
                return (
                  <li key={t.id} className={cn('flex items-center gap-3 rounded-xl border p-3 transition', t.is_completed ? 'border-emerald-100 bg-emerald-50/40' : 'border-slate-200')}>
                    <button disabled={t.is_completed || closed} onClick={() => doneM.mutate(t.id)} aria-label="Mark complete" className="shrink-0">
                      {t.is_completed ? <CheckCircle2 className="h-5 w-5 text-emerald-500" /> : <Circle className="h-5 w-5 text-slate-300 hover:text-royal-500" />}
                    </button>
                    <span className={cn('flex-1 text-sm', t.is_completed ? 'text-slate-400 line-through' : 'font-medium text-slate-800')}>{t.title}</span>
                    <span className={cn('text-xs', !t.is_completed && d !== null && d < 0 ? 'font-semibold text-rose-600' : 'text-slate-400')}>{t.is_completed ? fmtDate(t.completed_at) : fmtDate(t.due_date)}</span>
                  </li>
                )
              })}
            </ul>
            {!closed && (
              <div className="mt-4 flex gap-2">
                <Input value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="Add a follow-up task" wrapperClassName="flex-1" />
                <Button variant="secondary" disabled={!taskTitle.trim()} loading={taskM.isPending} onClick={() => taskM.mutate()} leftIcon={<Plus className="h-4 w-4" />}>Add</Button>
              </div>
            )}
          </Card>
          {c.closure_notes && <Card title="Closure"><p className="text-sm text-slate-700">{c.closure_notes}</p>{c.is_exception_closure && <p className="mt-2 text-xs font-semibold text-amber-700">Closed by exception</p>}</Card>}
        </div>

        <div className="space-y-6">
          <Card title="Participants" subtitle="Lead speaks for AICTE; supporting bureaus feed the lead">
            <ul className="space-y-2.5">
              {c.participants.map((p) => {
                const b = p.bureau_id ? byId.get(p.bureau_id) : undefined
                const isLead = p.role_in_coordination === 'lead' || (lead && p.bureau_id === lead.id)
                return (
                  <li key={p.id} className={cn('flex items-center gap-3 rounded-xl p-3', isLead ? 'bg-gradient-to-r from-gold-50 to-white ring-1 ring-gold-200' : 'bg-slate-50')}>
                    {b ? <BureauChip code={b.code} /> : <span className="chip border-slate-200 bg-white text-slate-600">Officer #{p.user_id}</span>}
                    <span className="flex-1 truncate text-[13px] text-slate-600">{b?.name ?? p.role_in_coordination}</span>
                    {isLead && <span className="chip border-gold-200 bg-white text-gold-700"><Crown className="h-3 w-3" />Lead</span>}
                    {p.acknowledged ? <span className="chip border-emerald-200 bg-emerald-50 text-emerald-700"><Check className="h-3 w-3" />Ack</span> : <span className="chip border-amber-200 bg-amber-50 text-amber-700">Pending</span>}
                  </li>
                )
              })}
            </ul>
          </Card>
          <Card title="Timelines">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Acknowledge by</dt><dd className="font-semibold">{fmtDate(c.acknowledge_by)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Action due</dt><dd className={cn('font-semibold', due !== null && due < 0 && !closed && 'text-rose-600')}>{fmtDate(c.action_due_date)}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Opened</dt><dd>{fmtDateTime(c.created_at)}</dd></div>
            </dl>
          </Card>
        </div>
      </div>

      <Modal isOpen={closeOpen} onClose={() => setCloseOpen(false)} title="Close coordination" description="Closing coordination never closes a bureau's own case — each bureau closes its file with a cross-reference."
        footer={<><Button variant="secondary" onClick={() => setCloseOpen(false)}>Cancel</Button><Button variant="dark" disabled={!notes.trim() || (pendingAcks > 0 && !exception)} loading={closeM.isPending} onClick={() => closeM.mutate()}>Close coordination</Button></>}>
        <div className="space-y-3">
          {(pendingAcks > 0 || openTasks > 0) && (
            <p className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[13px] text-amber-800">
              {pendingAcks > 0 && <>{pendingAcks} bureau{pendingAcks > 1 ? 's have' : ' has'} not acknowledged yet. </>}
              {openTasks > 0 && <>{openTasks} follow-up task{openTasks > 1 ? 's are' : ' is'} still open. </>}
              {pendingAcks > 0 && 'Tick exception closure to proceed — it is recorded in the audit trail.'}
            </p>
          )}
          <Textarea label="Closure notes" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" checked={exception} onChange={(e) => setException(e.target.checked)} className="rounded border-slate-300" />Exception closure (some acknowledgements pending)</label>
        </div>
      </Modal>
      <Modal isOpen={decisionOpen} onClose={() => setDecisionOpen(false)} title="Record coordination decision"
        footer={<><Button variant="secondary" onClick={() => setDecisionOpen(false)}>Cancel</Button><Button loading={decM.isPending} onClick={() => decM.mutate()}>Save decision</Button></>}>
        <div className="space-y-3">
          <Select label="Decision" value={decision} onChange={(e) => setDecision(e.target.value)} options={[
            { value: 'coordinate', label: 'Coordinate under lead bureau' }, { value: 'link_related', label: 'Link as related, act separately' },
            { value: 'keep_separate', label: 'Keep separate' }, { value: 'escalate', label: 'Escalate to competent authority' }, { value: 'dismiss', label: 'Dismiss' },
          ]} />
          <Textarea label="Rationale" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </Modal>
    </div>
  )
}
