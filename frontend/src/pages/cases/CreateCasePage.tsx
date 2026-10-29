import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { addDays, format } from 'date-fns'
import {
  AlertOctagon, ArrowRight, Building2, CheckCircle2, Fingerprint, Languages, Link2, Loader2, Radar, Search, Sparkles, Wand2,
} from 'lucide-react'
import { createCase, getCase } from '../../api/cases'
import { resolveInstitution } from '../../api/intelligence'
import { listInstitutions } from '../../api/institutions'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { BureauChip, Button, Card, Input, Meter, Modal, Select, Textarea } from '../../components/ui'
import { useAuth } from '../../contexts/AuthContext'
import { useBureaus, useDebounce } from '../../hooks/useData'
import { toast } from '../../hooks/useToast'
import { CATEGORIES } from '../../lib/domain'
import { cn } from '../../lib/cn'
import type { Case, ResolveCandidate } from '../../types'

const BAND: Record<string, { label: string; tone: string; bar: string }> = {
  confirmed: { label: 'Confirmed', tone: 'text-emerald-700 bg-emerald-50 border-emerald-200', bar: 'from-emerald-500 to-emerald-400' },
  high: { label: 'High confidence', tone: 'text-royal-700 bg-royal-50 border-royal-200', bar: 'from-royal-500 to-royal-400' },
  probable: { label: 'Probable — verify', tone: 'text-amber-700 bg-amber-50 border-amber-200', bar: 'from-amber-500 to-amber-400' },
  weak: { label: 'Weak', tone: 'text-slate-600 bg-slate-50 border-slate-200', bar: 'from-slate-400 to-slate-300' },
}

const SAMPLES = [
  'Students of A.I.E.T. Faridabad are charged extra fees',
  'मारवाड़ इंजीनियरिंग कॉलेज जोधपुर के विरुद्ध शिकायत',
  'Kavery Instt of Tech, Mysore not returning certificates',
  'AICTE ID 1-2847561093 hostel issue',
]

const TIMELINE_DAYS: Record<string, number> = { PGRC: 30, RB: 60, AB: 45, ACAD: 45, FIN: 30 }

export function CandidateCard({ c, selected, onSelect, rank }: { c: ResolveCandidate; selected?: boolean; onSelect?: () => void; rank: number }) {
  const band = BAND[c.band]
  return (
    <div
      className={cn('rounded-2xl border bg-white p-4 transition-all', selected ? 'border-emerald-300 shadow-[0_0_0_4px_rgba(16,185,129,.12)]' : 'border-slate-200 hover:border-royal-200')}
      style={{ animation: `fade-up .45s var(--ease-out) ${rank * 0.06}s both` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-slate-900">{c.canonical_name}</p>
          <p className="text-xs text-slate-500">{[c.short_name, c.city, c.state].filter(Boolean).join(' · ')} {c.aicte_id && <span className="font-mono">· {c.aicte_id}</span>}</p>
        </div>
        <div className="text-right">
          <p className="text-lg font-extrabold leading-none text-slate-900 tabular">{Math.round(c.confidence * 100)}%</p>
          <span className={cn('chip mt-1', band.tone)}>{band.label}</span>
        </div>
      </div>
      <Meter value={c.confidence * 100} className="mt-3" barClassName={band.bar} />
      <div className="mt-3 flex flex-wrap gap-1.5">
        {c.evidence.map((e) => (
          <span key={e.signal + e.detail} className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600" title={`strength ${e.strength}`}>
            <span className="font-bold uppercase tracking-wide text-slate-500">{e.signal.replace('_', ' ')}</span> {e.detail}
          </span>
        ))}
        {c.conflicts.map((x) => <span key={x} className="rounded-md bg-rose-50 px-2 py-0.5 text-[11px] text-rose-600">⚠ {x}</span>)}
      </div>
      {onSelect && (
        <div className="mt-3 flex justify-end">
          <Button size="sm" variant={selected ? 'success' : 'secondary'} leftIcon={selected ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Link2 className="h-3.5 w-3.5" />} onClick={onSelect}>
            {selected ? 'Linked' : 'Link this institution'}
          </Button>
        </div>
      )}
    </div>
  )
}

export default function CreateCasePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { bureaus, byId } = useBureaus()
  const [text, setText] = useState('')
  const [writtenName, setWrittenName] = useState('')
  const [institutionId, setInstitutionId] = useState<number | null>(null)
  const [institutionLabel, setInstitutionLabel] = useState('')
  const [manual, setManual] = useState('')
  const [created, setCreated] = useState<Case | null>(null)
  const [form, setForm] = useState({
    title: '', category: 'Fee Refund', priority: 'medium', bureau_id: '', source_case_id: '',
    complainant_name: '', complainant_email: '', complainant_phone: '', received_date: format(new Date(), 'yyyy-MM-dd'),
    due_date: '', next_action: 'Examine complaint and seek institution\'s response',
  })
  const up = (k: keyof typeof form, v: string) => setForm((f) => ({ ...f, [k]: v }))

  useEffect(() => {
    if (!form.bureau_id && user?.bureau_id) up('bureau_id', String(user.bureau_id))
    else if (!form.bureau_id && bureaus.length) up('bureau_id', String(bureaus.find((b) => b.code === 'PGRC')?.id ?? bureaus[0].id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, bureaus])

  const code = byId.get(Number(form.bureau_id))?.code ?? ''
  useEffect(() => {
    const days = TIMELINE_DAYS[code] ?? 45
    setForm((f) => ({ ...f, due_date: format(addDays(new Date(f.received_date || new Date()), days), 'yyyy-MM-dd') }))
  }, [code, form.received_date])

  const probe = useDebounce(`${writtenName} ${text}`.trim(), 450)
  const resolveQ = useQuery({
    queryKey: ['resolve', probe],
    queryFn: () => resolveInstitution({ text, name: writtenName || undefined, top_k: 4 }),
    enabled: probe.length >= 4,
  })
  const manualQ = useQuery({
    queryKey: ['inst-search', manual],
    queryFn: () => listInstitutions({ search: manual, limit: 6 }),
    enabled: manual.length >= 2,
  })

  // Auto-link when the engine is confident and unambiguous
  useEffect(() => {
    const r = resolveQ.data
    if (r && r.decision === 'auto_link_suggested' && r.candidates[0] && !institutionId) {
      setInstitutionId(r.candidates[0].institution_id)
      setInstitutionLabel(r.candidates[0].canonical_name)
    }
  }, [resolveQ.data, institutionId])

  const submit = useMutation({
    mutationFn: async () => {
      const c = await createCase({
        title: form.title, summary: text || undefined, category: form.category, priority: form.priority,
        institution_id: institutionId, bureau_id: Number(form.bureau_id) || undefined, source_case_id: form.source_case_id || undefined,
        complainant_name: form.complainant_name || undefined, complainant_email: form.complainant_email || undefined,
        complainant_phone: form.complainant_phone || undefined, received_date: form.received_date ? new Date(form.received_date).toISOString() : undefined,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : undefined, next_action: form.next_action || undefined,
      })
      return getCase(c.id).catch(() => c)
    },
    onSuccess: (c) => {
      toast.success(`${c.case_number} registered`)
      if (c.overlap_bureaus?.length) setCreated(c)
      else navigate(`/cases/${c.id}`)
    },
    onError: (e) => toast.error(apiError(e, 'Could not register complaint')),
  })

  const errors = useMemo(() => ({
    title: form.title.trim().length < 5 ? 'Give a short descriptive title' : '',
    institution: !institutionId ? 'Link the institution' : '',
  }), [form.title, institutionId])
  const canSubmit = !errors.title && !errors.institution

  return (
    <div>
      <PageHeader
        breadcrumbs={[{ label: 'Cases', href: '/cases' }, { label: 'Register complaint' }]}
        eyebrow="Single entry point for every Bureau / Cell"
        title="Register a complaint"
        description="Paste the complaint as received. NYAYA SETU identifies the institution — even from acronyms, typos, Hindi text, an e-mail or an address — and warns you if another bureau is already handling it."
      />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_1fr] [&>*]:min-w-0">
        <div className="space-y-6">
          <Card title="1 · Complaint as received" icon={<Languages className="h-5 w-5" />} subtitle="Any language or format — CPGRAMS text, e-mail, letter">
            <div className="space-y-4">
              <Textarea
                rows={5}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="e.g. Students of A.I.E.T. Faridabad are being charged ₹45,000 over the approved fee…"
              />
              <div className="flex flex-wrap gap-1.5">
                <span className="mr-1 inline-flex items-center gap-1 text-[11px] font-semibold text-slate-400"><Wand2 className="h-3 w-3" />Try:</span>
                {SAMPLES.map((s) => (
                  <button key={s} onClick={() => { setText(s); setInstitutionId(null) }} className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600 transition hover:border-royal-300 hover:text-royal-700">
                    {s.length > 42 ? s.slice(0, 40) + '…' : s}
                  </button>
                ))}
              </div>
              <Input label="Institution as written by the complainant (optional)" value={writtenName} onChange={(e) => { setWrittenName(e.target.value); setInstitutionId(null) }} placeholder="e.g. Aravli Inst of Engg, Faridabad" />
            </div>
          </Card>

          <Card title="2 · Case details" icon={<Building2 className="h-5 w-5" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input wrapperClassName="sm:col-span-2" label="Title" required value={form.title} onChange={(e) => up('title', e.target.value)} placeholder="Short description of the grievance" error={form.title && errors.title ? errors.title : undefined} />
              <Select label="Nature / category" value={form.category} onChange={(e) => up('category', e.target.value)} options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
              <Select label="Handling Bureau / Cell" value={form.bureau_id} onChange={(e) => up('bureau_id', e.target.value)} disabled={user?.role === 'bureau_officer'} options={bureaus.map((b) => ({ value: String(b.id), label: `${b.code} — ${b.name}` }))} />
              <Select label="Priority" value={form.priority} onChange={(e) => up('priority', e.target.value)} options={['low', 'medium', 'high', 'urgent'].map((p) => ({ value: p, label: p[0].toUpperCase() + p.slice(1) }))} />
              <Input label="Source reference" value={form.source_case_id} onChange={(e) => up('source_case_id', e.target.value)} placeholder="CPGRAMS reg. no. / e-Office file no." />
              <Input label="Date of receipt" type="date" value={form.received_date} onChange={(e) => up('received_date', e.target.value)} />
              <Input label="Expected disposal date" type="date" value={form.due_date} onChange={(e) => up('due_date', e.target.value)} hint={code ? `Suggested from ${code} timeline rule (configurable)` : undefined} />
              <Input label="Complainant name" value={form.complainant_name} onChange={(e) => up('complainant_name', e.target.value)} />
              <Input label="Complainant e-mail" type="email" value={form.complainant_email} onChange={(e) => up('complainant_email', e.target.value)} />
              <Input wrapperClassName="sm:col-span-2" label="Next action required" value={form.next_action} onChange={(e) => up('next_action', e.target.value)} />
            </div>
          </Card>
        </div>

        <div className="space-y-6 xl:sticky xl:top-24 xl:self-start">
          <Card
            title={<span className="flex items-center gap-2">Institution identity <span className="chip border-gold-200 bg-gold-50 text-gold-700"><Sparkles className="h-3 w-3" />IRE 2.0</span></span>}
            icon={<Fingerprint className="h-5 w-5" />}
            subtitle="Offline engine · explainable evidence · officer confirms"
          >
            {institutionId && (
              <div className="mb-4 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-3">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <div className="min-w-0 flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">Linked institution</p>
                  <p className="truncate text-sm font-bold text-slate-900">{institutionLabel}</p>
                </div>
                <button onClick={() => setInstitutionId(null)} className="text-xs font-semibold text-emerald-700 hover:underline">Change</button>
              </div>
            )}
            {probe.length < 4 ? (
              <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-center">
                <Fingerprint className="mx-auto h-8 w-8 text-slate-300" />
                <p className="mt-2 text-sm text-slate-500">Start typing the complaint — candidates appear here with the evidence behind each match.</p>
              </div>
            ) : resolveQ.isFetching && !resolveQ.data ? (
              <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" /> Resolving identity…</div>
            ) : resolveQ.data ? (
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className={cn('chip', resolveQ.data.decision === 'auto_link_suggested' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : resolveQ.data.decision === 'no_match' ? 'border-slate-200 bg-slate-50 text-slate-600' : 'border-amber-200 bg-amber-50 text-amber-700')}>
                    {resolveQ.data.decision === 'auto_link_suggested' ? 'Confident match' : resolveQ.data.decision === 'no_match' ? 'No registry match' : 'Officer confirmation required'}
                  </span>
                  {resolveQ.data.ambiguous && <span className="chip border-amber-200 bg-amber-50 text-amber-700">Ambiguous — similar institutions</span>}
                  {resolveQ.data.signals.transliterated && <span className="chip border-violet-200 bg-violet-50 text-violet-700">Hindi transliterated</span>}
                  {resolveQ.data.signals.aicte_ids.map((x) => <span key={x} className="chip border-royal-200 bg-royal-50 font-mono text-royal-700">{x}</span>)}
                  <span className="ml-auto text-slate-400">{resolveQ.data.registry_size} institutions searched</span>
                </div>
                {resolveQ.data.candidates.map((c, i) => (
                  <CandidateCard key={c.institution_id} c={c} rank={i} selected={institutionId === c.institution_id}
                    onSelect={() => { setInstitutionId(c.institution_id); setInstitutionLabel(c.canonical_name) }} />
                ))}
                {resolveQ.data.candidates.length === 0 && <p className="py-4 text-center text-sm text-slate-500">No likely institution found. Search the registry below.</p>}
              </div>
            ) : null}

            <div className="mt-5 border-t border-slate-100 pt-4">
              <Input leftIcon={<Search className="h-4 w-4" />} label="Or search the registry manually" value={manual} onChange={(e) => setManual(e.target.value)} placeholder="Name, acronym or city" />
              {manualQ.data && manual.length >= 2 && (
                <div className="mt-2 divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200">
                  {manualQ.data.items.map((i) => (
                    <button key={i.id} onClick={() => { setInstitutionId(i.id); setInstitutionLabel(i.canonical_name); setManual('') }} className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-royal-50">
                      <span className="truncate">{i.canonical_name}</span>
                      <span className="text-xs text-slate-400">{i.city}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Card>

          <div className="card flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-slate-600">
              {errors.institution || errors.title ? (
                <span className="text-slate-500">{[errors.institution, errors.title].filter(Boolean).join(' · ')}</span>
              ) : (
                <span className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Ready — overlap check runs on save</span>
              )}
            </div>
            <Button size="lg" disabled={!canSubmit} loading={submit.isPending} onClick={() => submit.mutate()} rightIcon={<ArrowRight className="h-4 w-4" />}>
              Register complaint
            </Button>
          </div>
        </div>
      </div>

      <Modal
        isOpen={!!created}
        onClose={() => created && navigate(`/cases/${created.id}`)}
        title="Potential Overlapping Cases – Coordination Required"
        icon={<AlertOctagon className="h-5 w-5 text-rose-600" />}
        description={created ? `${created.case_number} has been registered.` : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={() => created && navigate(`/cases/${created.id}`)}>Open the new case</Button>
            <Button variant="gold" leftIcon={<Radar className="h-4 w-4" />} onClick={() => created && navigate(`/overlaps?institution=${created.institution_id}`)}>Review overlap</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          <b>{created?.institution?.canonical_name}</b> already has open files with:
        </p>
        <div className="mt-3 flex flex-wrap gap-2">{created?.overlap_bureaus?.map((b) => <BureauChip key={b} code={b} name />)}</div>
        <p className="mt-4 rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
          The concerned bureaus and coordination reviewers have been alerted. Agree a lead bureau before writing to the institution, so it receives one consistent communication.
        </p>
      </Modal>
    </div>
  )
}
