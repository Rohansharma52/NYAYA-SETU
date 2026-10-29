import { useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Eye, AlertOctagon, ArrowLeftRight, ArrowRight, CalendarClock, Check, Download, FileText, Flag, MessageSquarePlus, Paperclip,
  Radar, UploadCloud, UserCheck,
} from 'lucide-react'
import {
  addAction, assignCase, caseTransfers, changeStatus, downloadAttachment, getCase, listAttachments, requestTransfer, uploadAttachment,
} from '../../api/cases'
import { officerDirectory } from '../../api/users'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  BureauChip, Button, ButtonLink, Card, DataNote, EmptyState, ErrorState, Modal, PageSkeleton, PriorityBadge, Select, StatusBadge,
  Textarea, Timeline,
} from '../../components/ui'
import { useBureaus } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { STATUS_META, VALID_TRANSITIONS } from '../../lib/domain'
import { daysUntil, downloadBlob, fmtDate, fmtDateTime, fromNow, titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'

const STAGES = [
  { key: 'received', label: 'Received', match: ['received'] },
  { key: 'triaged', label: 'Triaged', match: ['triaged', 'reopened'] },
  { key: 'assigned', label: 'Assigned', match: ['assigned', 'transfer_requested', 'transferred'] },
  { key: 'under_process', label: 'Under process', match: ['under_process', 'awaiting_information', 'escalated'] },
  { key: 'decision_review', label: 'Decision', match: ['decision_review'] },
  { key: 'disposed', label: 'Disposed', match: ['disposed', 'closed'] },
]

function Fact({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('rounded-xl bg-slate-50/80 p-3', className)}>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <div className="mt-1 text-sm font-medium text-slate-800">{children}</div>
    </div>
  )
}

export default function CaseDetailPage() {
  const { id } = useParams()
  const caseId = Number(id)
  const qc = useQueryClient()
  const { bureaus } = useBureaus()
  const fileRef = useRef<HTMLInputElement>(null)
  const [modal, setModal] = useState<null | 'status' | 'assign' | 'note' | 'transfer'>(null)
  const [statusTo, setStatusTo] = useState('')
  const [reason, setReason] = useState('')
  const [officer, setOfficer] = useState('')
  const [toBureau, setToBureau] = useState('')
  const [noteType, setNoteType] = useState('note')
  const [file, setFile] = useState<File | null>(null)

  const q = useQuery({ queryKey: ['case', caseId], queryFn: () => getCase(caseId) })
  const attachments = useQuery({ queryKey: ['case', caseId, 'attachments'], queryFn: () => listAttachments(caseId) })
  const transfers = useQuery({ queryKey: ['case', caseId, 'transfers'], queryFn: () => caseTransfers(caseId) })
  const directory = useQuery({ queryKey: ['directory', q.data?.bureau_id], queryFn: () => officerDirectory(q.data?.bureau_id ?? undefined), enabled: modal === 'assign' })

  const done = (msg: string) => {
    toast.success(msg)
    setModal(null)
    setReason('')
    setFile(null)
    qc.invalidateQueries({ queryKey: ['case', caseId] })
    qc.invalidateQueries({ queryKey: ['cases'] })
    qc.invalidateQueries({ queryKey: ['overview'] })
  }
  const fail = (e: unknown) => toast.error(apiError(e))
  const statusM = useMutation({ mutationFn: () => changeStatus(caseId, { new_status: statusTo, reason }), onSuccess: () => done('Status updated'), onError: fail })
  const assignM = useMutation({ mutationFn: () => assignCase(caseId, { officer_id: Number(officer), notes: reason || undefined }), onSuccess: () => done('Officer assigned'), onError: fail })
  const transferM = useMutation({ mutationFn: () => requestTransfer(caseId, { to_bureau_id: Number(toBureau), reason }), onSuccess: () => done('Transfer requested — receiving bureau alerted'), onError: fail })
  const noteM = useMutation({
    mutationFn: async () => {
      if (file) await uploadAttachment(caseId, file, reason || undefined)
      else await addAction(caseId, { action_type: noteType, description: reason })
    },
    onSuccess: () => done(file ? 'Document attached' : 'Action recorded'),
    onError: fail,
  })

  if (q.isLoading) return <PageSkeleton />
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} message="This case does not exist or was removed." />
  const c = q.data
  const due = daysUntil(c.due_date)
  const open = !['disposed', 'closed', 'transferred'].includes(c.status)
  const stageIdx = STAGES.findIndex((s) => s.match.includes(c.status))
  const allowed = VALID_TRANSITIONS[c.status] ?? []
  const actions = [...(c.actions ?? [])].sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''))
  const last = actions[0]
  const canAct = c.can_act !== false

  return (
    <div>
      <PageHeader
        docTitle={c.case_number}
        breadcrumbs={[{ label: 'Cases', href: '/cases' }, { label: c.case_number }]}
        eyebrow={<span className="font-mono normal-case tracking-normal">{c.case_number}{c.source_case_id ? ` · ${c.source_case_id}` : ''}</span>}
        title={c.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={c.status} />
            <PriorityBadge priority={c.priority} />
            <BureauChip code={c.bureau?.code} name />
            <Link to={`/institutions/${c.institution_id}`} className="font-semibold text-royal-600 hover:underline">{c.institution?.canonical_name}</Link>
          </span>
        }
        actions={canAct && (
          <>
            <Button variant="secondary" leftIcon={<MessageSquarePlus className="h-4 w-4" />} onClick={() => setModal('note')}>Add action</Button>
            <Button variant="secondary" leftIcon={<UserCheck className="h-4 w-4" />} onClick={() => setModal('assign')}>Assign</Button>
            {open && <Button variant="secondary" leftIcon={<ArrowLeftRight className="h-4 w-4" />} onClick={() => setModal('transfer')}>Transfer</Button>}
            <Button leftIcon={<Flag className="h-4 w-4" />} disabled={!allowed.length} onClick={() => { setStatusTo(allowed[0] ?? ''); setModal('status') }}>Update status</Button>
          </>
        )}
      />

      {!canAct && (
        <div className="mb-4 flex flex-col gap-3 rounded-2xl border border-royal-200 bg-royal-50/70 p-4 sm:flex-row sm:items-center">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-royal-500 text-white"><Eye className="h-5 w-5" /></span>
          <div className="flex-1">
            <p className="text-sm font-bold text-royal-800">Read-only view — this file is handled by {c.bureau?.code ?? 'another Bureau/Cell'}</p>
            <p className="text-[13px] text-royal-700/80">You can see its status and history so your bureau does not act twice. Only {c.bureau?.code ?? 'the handling bureau'} can update it; coordinate through the Overlap Radar.</p>
          </div>
          <ButtonLink to={`/overlaps?institution=${c.institution_id}`} variant="secondary" size="sm" leftIcon={<Radar className="h-4 w-4" />}>Coordinate</ButtonLink>
        </div>
      )}

      {!!c.overlap_bureaus?.length && (
        <div className="mb-6 flex animate-fade-up flex-col gap-3 rounded-2xl border border-rose-200 bg-gradient-to-r from-rose-50 to-white p-4 sm:flex-row sm:items-center">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-500 text-white shadow-[0_8px_20px_-8px_rgba(244,63,94,.8)]"><AlertOctagon className="h-5 w-5" /></span>
          <div className="flex-1">
            <p className="text-sm font-bold text-rose-800">Potential Overlapping Cases – Coordination Required</p>
            <p className="text-[13px] text-rose-700/80">This institution also has open files with {c.overlap_bureaus.join(', ')}. Check before writing to the institution.</p>
          </div>
          <ButtonLink to={`/overlaps?institution=${c.institution_id}`} variant="danger" size="sm" leftIcon={<Radar className="h-4 w-4" />}>Open overlap analysis</ButtonLink>
        </div>
      )}

      {/* Lifecycle */}
      <div className="card mb-6 overflow-x-auto p-5">
        <ol className="flex min-w-[640px] items-center">
          {STAGES.map((s, i) => {
            const reached = i <= stageIdx
            const current = i === stageIdx
            return (
              <li key={s.key} className="flex flex-1 items-center last:flex-none">
                <div className="flex flex-col items-center gap-1.5">
                  <span className={cn('flex h-9 w-9 items-center justify-center rounded-full border-2 text-xs font-bold transition-all duration-500',
                    current ? (c.status === 'escalated' ? 'border-rose-500 bg-rose-500 text-white shadow-[0_0_0_6px_rgba(244,63,94,.15)]' : 'border-royal-500 bg-royal-500 text-white shadow-[0_0_0_6px_rgba(91,102,236,.15)]')
                      : reached ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-slate-200 bg-white text-slate-400')}>
                    {reached && !current ? <Check className="h-4 w-4" /> : i + 1}
                  </span>
                  <span className={cn('whitespace-nowrap text-[11px] font-semibold', current ? 'text-slate-900' : 'text-slate-400')}>
                    {current ? STATUS_META[c.status]?.label ?? s.label : s.label}
                  </span>
                </div>
                {i < STAGES.length - 1 && <span className={cn('mx-2 mb-5 h-0.5 flex-1 rounded-full', i < stageIdx ? 'bg-emerald-400' : 'bg-slate-200')} />}
              </li>
            )
          })}
        </ol>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_1fr] [&>*]:min-w-0">
        <div className="space-y-6">
          <Card title="Case tracking" subtitle="PS 26264 §2 — complete status and movement" icon={<FileText className="h-5 w-5" />}>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <Fact label="Unique case ID"><span className="font-mono text-[13px]">{c.case_number}</span></Fact>
              <Fact label="Source reference"><span className="font-mono text-[13px]">{c.source_case_id ?? '—'}</span></Fact>
              <Fact label="Date of receipt">{fmtDate(c.received_date)}</Fact>
              <Fact label="Nature / category">{c.category}</Fact>
              <Fact label="Current status"><StatusBadge status={c.status} /></Fact>
              <Fact label="Presently with"><span className="flex items-center gap-1.5"><BureauChip code={c.bureau?.code} /><span className="truncate text-xs text-slate-500">{c.bureau?.name}</span></span></Fact>
              <Fact label="Assigned officer">{c.assigned_officer?.full_name ?? <span className="text-slate-400">Unassigned</span>}</Fact>
              <Fact label="Date of last action">{c.last_action_date ? `${fmtDate(c.last_action_date)} (${fromNow(c.last_action_date)})` : '—'}</Fact>
              <Fact label="Expected disposal">
                {fmtDate(c.due_date)}
                {due !== null && open && (
                  <span className={cn('ml-1.5 text-xs font-bold', due < 0 ? 'text-rose-600' : due <= 7 ? 'text-amber-600' : 'text-emerald-600')}>
                    {due < 0 ? `${-due}d overdue` : `${due}d left`}
                  </span>
                )}
              </Fact>
              <Fact label="Last action taken" className="sm:col-span-2 lg:col-span-3">{c.last_action ?? last?.description ?? '—'}</Fact>
              <Fact label="Next action required" className="border border-royal-100 bg-royal-50/60 sm:col-span-2 lg:col-span-3">
                <span className="flex items-center gap-2"><CalendarClock className="h-4 w-4 text-royal-500" />{c.next_action ?? '—'}</span>
              </Fact>
            </div>
            {c.summary && (
              <div className="mt-4 rounded-xl border border-slate-100 p-4">
                <p className="label-eyebrow">Complaint text</p>
                <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed text-slate-700">{c.summary}</p>
              </div>
            )}
            {(c.complainant_name || c.complainant_email) && (
              <p className="mt-3 text-xs text-slate-500">Complainant: <b className="text-slate-700">{c.complainant_name}</b> {c.complainant_email && `· ${c.complainant_email}`}</p>
            )}
          </Card>

          <Card
            title="Supporting documents"
            subtitle="Stored with SHA-256 fingerprint for integrity"
            icon={<Paperclip className="h-5 w-5" />}
            action={canAct ? <Button size="sm" variant="secondary" leftIcon={<UploadCloud className="h-3.5 w-3.5" />} onClick={() => { setNoteType('document'); setModal('note') }}>Attach</Button> : undefined}
          >
            {(attachments.data ?? []).length === 0 ? (
              <EmptyState icon={Paperclip} title="No documents yet" description="Attach replies, inspection reports or orders with remarks." className="py-8" />
            ) : (
              <ul className="divide-y divide-slate-100">
                {attachments.data!.map((a) => (
                  <li key={a.id} className="flex items-center gap-3 py-2.5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-600"><FileText className="h-4 w-4" /></span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">{a.filename}</p>
                      <p className="truncate text-xs text-slate-400">{(a.size_bytes / 1024).toFixed(1)} KB · {a.uploaded_by} · {fmtDateTime(a.created_at)} · <span className="font-mono">{a.sha256.slice(0, 10)}…</span></p>
                      {a.remarks && <p className="text-xs text-slate-500">{a.remarks}</p>}
                    </div>
                    {canAct ? (
                      <Button size="xs" variant="ghost" leftIcon={<Download className="h-3.5 w-3.5" />} onClick={async () => {
                        try { downloadBlob(await downloadAttachment(caseId, a), a.filename) } catch { toast.error('Could not download the document') }
                      }}>Get</Button>
                    ) : <span className="text-[11px] text-slate-400">Handling bureau only</span>}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {(transfers.data ?? []).length > 0 && (
            <Card title="Transfer / escalation history" icon={<ArrowLeftRight className="h-5 w-5" />}>
              <ul className="space-y-2">
                {transfers.data!.map((t) => (
                  <li key={t.id} className="flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 p-3 text-sm">
                    <BureauChip code={t.from_bureau} /> <ArrowRight className="h-3.5 w-3.5 text-slate-400" /> <BureauChip code={t.to_bureau} />
                    <span className={cn('chip', t.status === 'accepted' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : t.status === 'rejected' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-cyan-200 bg-cyan-50 text-cyan-700')}>{titleCase(t.status)}</span>
                    <span className="text-xs text-slate-500">{t.reason}</span>
                    <span className="ml-auto text-xs text-slate-400">{fmtDate(t.requested_at)}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>

        <Card title="Workflow & action history" subtitle="Chronological — officer, bureau, date & time stamp" icon={<CalendarClock className="h-5 w-5" />} className="xl:self-start">
          <Timeline
            events={actions.map((a) => ({
              id: a.id, type: a.action_type, description: a.description, performedBy: a.performed_by?.full_name,
              createdAt: a.created_at,
            }))}
          />
        </Card>
      </div>
      <div className="mt-6"><DataNote /></div>

      {/* Modals */}
      <Modal isOpen={modal === 'status'} onClose={() => setModal(null)} title="Update status" description="Only valid lifecycle transitions are allowed. A reason is mandatory and audit-logged."
        footer={<><Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button><Button loading={statusM.isPending} disabled={!statusTo || !reason.trim()} onClick={() => statusM.mutate()}>Update</Button></>}>
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {allowed.map((s) => (
              <button key={s} onClick={() => setStatusTo(s)} className={cn('rounded-xl border px-3 py-2 text-sm font-semibold transition', statusTo === s ? 'border-royal-400 bg-royal-50 text-royal-800 shadow-soft' : 'border-slate-200 text-slate-600 hover:border-slate-300')}>
                {STATUS_META[s]?.label ?? s}
              </button>
            ))}
          </div>
          <Textarea label="Reason / remarks" required rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal isOpen={modal === 'assign'} onClose={() => setModal(null)} title="Assign officer"
        footer={<><Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button><Button loading={assignM.isPending} disabled={!officer} onClick={() => assignM.mutate()}>Assign</Button></>}>
        <div className="space-y-4">
          <Select label="Officer" value={officer} onChange={(e) => setOfficer(e.target.value)} placeholder="Select officer"
            options={(directory.data ?? []).map((u) => ({ value: String(u.id), label: `${u.full_name}${u.designation ? ' — ' + u.designation : ''}` }))} />
          <Textarea label="Notes" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal isOpen={modal === 'transfer'} onClose={() => setModal(null)} title="Request transfer" description="The receiving Bureau/Cell accepts or rejects. Overlapping files are flagged automatically."
        footer={<><Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button><Button loading={transferM.isPending} disabled={!toBureau || !reason.trim()} onClick={() => transferM.mutate()}>Request transfer</Button></>}>
        <div className="space-y-4">
          <Select label="Transfer to" value={toBureau} onChange={(e) => setToBureau(e.target.value)} placeholder="Select Bureau / Cell"
            options={bureaus.filter((b) => b.id !== c.bureau_id).map((b) => ({ value: String(b.id), label: `${b.code} — ${b.name}` }))} />
          <Textarea label="Reason" required rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </Modal>

      <Modal isOpen={modal === 'note'} onClose={() => setModal(null)} title="Record action / remarks" description="Optionally attach a supporting document (PDF, image, Word, Excel — max 10 MB)."
        footer={<><Button variant="secondary" onClick={() => setModal(null)}>Cancel</Button><Button loading={noteM.isPending} disabled={!reason.trim() && !file} onClick={() => noteM.mutate()}>Save</Button></>}>
        <div className="space-y-4">
          <Select label="Action type" value={noteType} onChange={(e) => setNoteType(e.target.value)} options={[
            { value: 'note', label: 'Remark / note' }, { value: 'letter_issued', label: 'Letter issued to institution' },
            { value: 'show_cause', label: 'Show-cause notice' }, { value: 'inspection', label: 'Inspection / visit' },
            { value: 'document', label: 'Supporting document' },
          ]} />
          <Textarea label="Remarks" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          <input ref={fileRef} type="file" className="hidden" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.txt,.csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button onClick={() => fileRef.current?.click()} className="flex w-full flex-col items-center justify-center gap-1 rounded-2xl border-2 border-dashed border-slate-200 p-5 text-sm text-slate-500 transition hover:border-royal-300 hover:bg-royal-50/40">
            <UploadCloud className="h-6 w-6 text-slate-400" />
            {file ? <span className="font-semibold text-slate-700">{file.name}</span> : 'Click to attach a supporting document'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
