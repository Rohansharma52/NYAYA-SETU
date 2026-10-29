import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FileUp, Upload, XCircle } from 'lucide-react'
import { commitImport, listImports, previewImport, type ImportPreviewResult } from '../../api/imports'
import { apiError } from '../../api/client'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, Segmented } from '../../components/ui'
import { toast } from '../../hooks/useToast'
import { fmtDateTime, titleCase } from '../../lib/format'
import { cn } from '../../lib/cn'

export default function ImportsPage() {
  const qc = useQueryClient()
  const ref = useRef<HTMLInputElement>(null)
  const [kind, setKind] = useState<'institutions' | 'cases'>('cases')
  const [preview, setPreview] = useState<ImportPreviewResult | null>(null)
  const [drag, setDrag] = useState(false)
  const jobs = useQuery({ queryKey: ['imports'], queryFn: listImports })
  const prev = useMutation({ mutationFn: (f: File) => previewImport(kind, f), onSuccess: setPreview, onError: (e) => toast.error(apiError(e)) })
  const commit = useMutation({
    mutationFn: () => commitImport(kind, preview!.job_id),
    onSuccess: () => { toast.success('Import committed — overlap detection runs on new cases'); setPreview(null); qc.invalidateQueries() },
    onError: (e) => toast.error(apiError(e)),
  })
  const cols = preview?.preview_rows[0] ? Object.keys(preview.preview_rows[0].data).slice(0, 6) : []
  return (
    <div>
      <PageHeader eyebrow="Integration-ready ingestion" title="Data imports"
        description="Bring in bureau registers, CPGRAMS exports or the AICTE institution master as CSV. Every row is validated and previewed — nothing is written until you commit."
        actions={<Segmented value={kind} onChange={(k) => { setKind(k); setPreview(null) }} options={[{ value: 'cases', label: 'Cases' }, { value: 'institutions', label: 'Institutions' }]} />} />
      <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr] [&>*]:min-w-0">
        <Card title={`Upload ${kind} CSV`} icon={<Upload className="h-5 w-5" />}>
          <input ref={ref} type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && prev.mutate(e.target.files[0])} />
          <button
            onClick={() => ref.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f) prev.mutate(f) }}
            className={cn('flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed p-10 text-center transition', drag ? 'border-royal-400 bg-royal-50' : 'border-slate-200 hover:border-royal-300 hover:bg-slate-50')}>
            <FileUp className="h-8 w-8 text-royal-400" />
            <span className="text-sm font-semibold text-slate-700">{prev.isPending ? 'Validating…' : 'Drop a CSV here or click to browse'}</span>
            <span className="text-xs text-slate-400">{kind === 'cases' ? 'title, category, institution_name / aicte_id, bureau_code, received_date, source_case_id…' : 'canonical_name, short_name, state, city, region, aicte_permanent_id…'}</span>
          </button>
          {preview && (
            <div className="mt-5 grid grid-cols-3 gap-3 text-center">
              <div className="rounded-xl bg-slate-50 p-3"><p className="text-xl font-extrabold">{preview.total_rows}</p><p className="text-xs text-slate-500">rows</p></div>
              <div className="rounded-xl bg-emerald-50 p-3"><p className="text-xl font-extrabold text-emerald-700">{preview.valid_rows}</p><p className="text-xs text-emerald-700">valid</p></div>
              <div className="rounded-xl bg-rose-50 p-3"><p className="text-xl font-extrabold text-rose-700">{preview.error_rows}</p><p className="text-xs text-rose-700">errors</p></div>
            </div>
          )}
          {preview && <Button className="mt-4 w-full" disabled={!preview.valid_rows} loading={commit.isPending} onClick={() => commit.mutate()}>Commit {preview.valid_rows} valid rows</Button>}
        </Card>
        <Card title={preview ? 'Preview' : 'Recent import jobs'} noPadding>
          {preview ? (
            <ul className="divide-y divide-slate-100">
              {preview.preview_rows.map((r) => {
                const d = r.data as Record<string, string>
                const main = d.title || d.canonical_name || d[cols[0]] || '—'
                const meta = cols.filter((c) => !['title', 'canonical_name', 'description', 'complaint_text'].includes(c)).slice(0, 4).map((c) => d[c]).filter(Boolean)
                const msgs = [...r.errors, ...r.warnings]
                return (
                  <li key={r.row} className="flex gap-3 px-5 py-3">
                    <span className="mt-0.5 w-5 shrink-0 text-xs font-semibold text-slate-400">{r.row}</span>
                    {r.status === 'valid' ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" /> : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">{main}</p>
                      <p className="truncate font-mono text-[11px] text-slate-400">{meta.join(' · ')}</p>
                      {msgs.length > 0 && <p className={cn('mt-1 text-xs', r.errors.length ? 'text-rose-600' : 'text-slate-500')}>{msgs.join('; ')}</p>}
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <ul className="divide-y divide-slate-100">
              {(jobs.data ?? []).map((j) => (
                <li key={j.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <span className="font-semibold">{j.filename}</span><span className="text-xs text-slate-400">{titleCase(j.import_type)}</span>
                  <span className="ml-auto text-xs text-slate-500">{j.imported_rows}/{j.total_rows} imported</span>
                  <span className={cn('chip', j.status === 'completed' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : j.status === 'failed' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-slate-200 bg-slate-50 text-slate-600')}>{titleCase(j.status)}</span>
                  <span className="text-xs text-slate-400">{fmtDateTime(j.created_at)}</span>
                </li>
              ))}
              {(jobs.data ?? []).length === 0 && <li className="p-10 text-center text-sm text-slate-400">No imports yet.</li>}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}
