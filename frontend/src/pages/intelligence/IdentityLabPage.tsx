import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from 'recharts'
import { Beaker, Fingerprint, Play, ShieldCheck, Sparkles, Target } from 'lucide-react'
import { getBenchmark, resolveInstitution } from '../../api/intelligence'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, DataNote, ErrorState, ScoreRing, SkeletonCard, Textarea } from '../../components/ui'
import { toast } from '../../hooks/useToast'
import { CandidateCard } from '../cases/CreateCasePage'
import { cn } from '../../lib/cn'

const EXAMPLES = [
  { label: 'Dotted acronym', text: 'Students of A.I.E.T. Faridabad are charged extra fees' },
  { label: 'Hindi letter', text: 'मारवाड़ इंजीनियरिंग कॉलेज जोधपुर के विरुद्ध शिकायत' },
  { label: 'Typos + abbreviations', text: 'Kavery Instt of Tech, Mysore' },
  { label: 'Only an ID', text: 'AICTE ID 1-2847561093 hostel issue' },
  { label: 'Only an e-mail', text: 'Reply received from director@acem-demo.ac.in rejecting our request' },
  { label: 'Address only', text: 'the college at Sinhgad road pune 411041 is harassing students' },
]

const COLORS = { exact: '#94A3B8', fuzzy: '#F59E0B', ire: '#5B66EC' }

export default function IdentityLabPage() {
  const [params] = useSearchParams()
  const [text, setText] = useState(params.get('q') ?? EXAMPLES[0].text)
  const bench = useQuery({ queryKey: ['benchmark'], queryFn: getBenchmark, staleTime: Infinity })
  const run = useMutation({ mutationFn: (t: string) => resolveInstitution({ text: t, top_k: 4 }), onError: (e) => toast.error(apiError(e)) })
  useEffect(() => { run.mutate(text) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const b = bench.data
  const variants = b ? Object.keys(b.methods.ire.by_variant) : []
  const chart = variants.map((v) => ({
    variant: (b!.dataset.variant_labels[v] ?? v).replace(' (must not match)', ''),
    'Exact lookup': Math.round(b!.methods.exact.by_variant[v] * 100),
    'Plain fuzzy': Math.round(b!.methods.fuzzy.by_variant[v] * 100),
    'NYAYA SETU IRE': Math.round(b!.methods.ire.by_variant[v] * 100),
  }))

  return (
    <div>
      <PageHeader
        eyebrow={<span className="flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5" />Innovation · data matching + rules + AI-assisted analytics</span>}
        title="Identity Lab"
        description="How NYAYA SETU recognises the same institution when complaint descriptions or references differ — and the measured accuracy behind it."
      />

      <div className="grid gap-6 xl:grid-cols-[1fr_1.05fr] [&>*]:min-w-0">
        <Card title="Try the engine" icon={<Fingerprint className="h-5 w-5" />} subtitle="Signals: AICTE ID · AISHE · domain · phone · pincode · location · acronym · fuzzy & transliterated name">
          <Textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} />
          <div className="mt-3 flex flex-wrap gap-1.5">
            {EXAMPLES.map((e) => (
              <button key={e.label} onClick={() => { setText(e.text); run.mutate(e.text) }} className={cn('rounded-full border px-2.5 py-1 text-[11px] font-semibold transition', text === e.text ? 'border-royal-300 bg-royal-50 text-royal-700' : 'border-slate-200 bg-white text-slate-600 hover:border-royal-200')}>
                {e.label}
              </button>
            ))}
          </div>
          <div className="mt-4 flex justify-end">
            <Button leftIcon={<Play className="h-4 w-4" />} loading={run.isPending} onClick={() => run.mutate(text)}>Resolve</Button>
          </div>
          {run.data && (
            <div className="mt-5 space-y-3 border-t border-slate-100 pt-5">
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="chip border-slate-200 bg-slate-50 text-slate-600">Decision: {run.data.decision.replace(/_/g, ' ')}</span>
                {run.data.signals.transliterated && <span className="chip border-violet-200 bg-violet-50 text-violet-700">Devanagari → Latin</span>}
                {[...run.data.signals.aicte_ids, ...run.data.signals.domains, ...run.data.signals.pincodes].map((x) => <span key={x} className="chip border-royal-200 bg-royal-50 font-mono text-royal-700">{x}</span>)}
              </div>
              <p className="rounded-lg bg-slate-50 px-3 py-2 font-mono text-[11px] text-slate-500">normalised: {run.data.signals.normalized_text}</p>
              {run.data.candidates.length === 0 && <p className="py-6 text-center text-sm text-slate-500">No institution in the registry matches — correctly abstains.</p>}
              {run.data.candidates.map((c, i) => <CandidateCard key={c.institution_id} c={c} rank={i} />)}
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card title="Benchmark" icon={<Target className="h-5 w-5" />} subtitle={b ? `${b.dataset.size} labelled snippets · ${b.dataset.institutions} institutions · seed ${b.dataset.seed} (reproducible)` : 'Loading…'}>
            {bench.isLoading ? <SkeletonCard /> : bench.isError || !b ? <ErrorState onRetry={() => bench.refetch()} /> : (
              <>
                <div className="grid grid-cols-3 gap-3">
                  {(['exact', 'fuzzy', 'ire'] as const).map((k) => (
                    <div key={k} className={cn('rounded-2xl p-4 text-center', k === 'ire' ? 'bg-gradient-to-b from-royal-50 to-white ring-1 ring-royal-200' : 'bg-slate-50')}>
                      <ScoreRing value={b.methods[k].f1 * 100} label={`${Math.round(b.methods[k].f1 * 100)}`} sublabel="F1" color={COLORS[k]} size={84} />
                      <p className={cn('mt-2 text-xs font-bold', k === 'ire' ? 'text-royal-700' : 'text-slate-600')}>{b.methods[k].label}</p>
                      <p className="mt-1 text-[11px] text-slate-500">P {Math.round(b.methods[k].precision * 100)}% · R {Math.round(b.methods[k].recall * 100)}%</p>
                    </div>
                  ))}
                </div>
                <div className="mt-5 h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chart} layout="vertical" margin={{ left: 40, right: 8, top: 4, bottom: 4 }} barGap={2}>
                      <CartesianGrid stroke="#EEF1F7" horizontal={false} />
                      <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: '#94A3B8' }} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="variant" width={150} tick={{ fontSize: 10.5, fill: '#475569' }} axisLine={false} tickLine={false} />
                      <RTooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} formatter={(v) => `${v}%`} />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      <Bar dataKey="Exact lookup" fill={COLORS.exact} radius={[0, 4, 4, 0]} barSize={6} />
                      <Bar dataKey="Plain fuzzy" fill={COLORS.fuzzy} radius={[0, 4, 4, 0]} barSize={6} />
                      <Bar dataKey="NYAYA SETU IRE" fill={COLORS.ire} radius={[0, 4, 4, 0]} barSize={6} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-3 flex gap-2 text-[11.5px] text-slate-500"><Beaker className="h-3.5 w-3.5 shrink-0" />{b.note}</p>
              </>
            )}
          </Card>
          <Card title="Why judges can trust it" icon={<ShieldCheck className="h-5 w-5" />}>
            <ul className="grid gap-2 text-[13px] text-slate-600 sm:grid-cols-2">
              {[
                'Runs fully offline — no complaint text leaves AICTE servers',
                'Every match lists its evidence; conflicting IDs reduce confidence',
                'Abstains when ambiguous instead of guessing',
                'Officer confirms every link; source records never altered',
              ].map((t) => <li key={t} className="flex gap-2 rounded-xl bg-slate-50 p-3"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />{t}</li>)}
            </ul>
          </Card>
        </div>
      </div>
      <div className="mt-6"><DataNote /></div>
    </div>
  )
}
