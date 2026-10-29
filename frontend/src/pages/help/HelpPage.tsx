import { Link } from 'react-router-dom'
import { BarChart3, BellRing, Building2, CheckCircle2, FilePlus2, Fingerprint, FolderKanban, GitMerge, LayoutDashboard, Radar, Search, Workflow } from 'lucide-react'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card } from '../../components/ui'

const DEMO = [
  { who: 'PGRC officer', email: 'officer2@aicte.demo', step: 'Register complaint → paste “Students of A.I.E.T. Faridabad are charged extra fees”. The identity engine links AIET from the acronym + city.', to: '/cases/new' },
  { who: 'System', email: '', step: 'On save, NYAYA SETU finds RB and FIN files on the same institution and raises “Potential Overlapping Cases – Coordination Required”.', to: '/overlaps' },
  { who: 'Coordination reviewer', email: 'reviewer@aicte.demo', step: 'Overlap Radar → AIET: see bureau lanes, rule C2 (parallel directions), the duplicate from the same complainant and the proposed lead (RB).', to: '/overlaps' },
  { who: 'Reviewer', email: 'reviewer@aicte.demo', step: 'Click “Start One-Voice coordination” — lead + supporting bureaus, tasks and deadlines are created; all officers are alerted.', to: '/coordination' },
  { who: 'Senior management', email: 'management@aicte.demo', step: 'Command Centre: totals, pending beyond timeline, bureau workload, disposal rate; Gangotri shows the critical “closure vs enforcement” conflict.', to: '/dashboard' },
  { who: 'Senior management', email: 'management@aicte.demo', step: 'Reports → monthly/quarterly performance, region-wise and overlap reports; Identity Lab → benchmark (F1 vs. baselines).', to: '/reports' },
]

const COVERAGE = [
  { icon: Building2, t: 'Centralized institution profile', d: 'Institution 360°: AICTE ID, AISHE, address, region, aliases, consolidated history, risk', to: '/institutions' },
  { icon: FolderKanban, t: 'Complaint / case tracking', d: 'Case ID, receipt date, category, status, bureau, officer, last & next action, expected disposal', to: '/cases' },
  { icon: Radar, t: 'Cross-bureau overlap detection', d: 'Automatic, explainable; duplicate / conflict / related / independent; lead bureau', to: '/overlaps' },
  { icon: LayoutDashboard, t: 'Real-time dashboard', d: 'Received, pending, under process, disposed, transferred, beyond timeline, institution & bureau workload', to: '/dashboard' },
  { icon: Workflow, t: 'Workflow & action history', d: 'Chronological actions with officer, bureau, timestamp, remarks, documents, transfers', to: '/cases' },
  { icon: Search, t: 'Search & filters', d: 'Name, AICTE ID, case ID, bureau, region, category, status, date range; Ctrl K anywhere', to: '/cases' },
  { icon: BellRing, t: 'Alerts & notifications', d: 'Overlap, pending reminders, escalation and timeline alerts every 15 minutes', to: '/notifications' },
  { icon: BarChart3, t: 'Reports & analytics', d: 'Bureau, region, institution, ageing, disposal rate, overlap, monthly & quarterly', to: '/reports' },
  { icon: Fingerprint, t: 'Innovation', d: 'Identity resolution across acronyms, typos, Hindi, IDs, e-mail and address — benchmarked', to: '/identity-lab' },
]

export function HelpContent() {
  return (
    <div className="space-y-6">
      <Card title="5-minute judge demo" subtitle="The exact example from PS 26264, end to end" icon={<FilePlus2 className="h-5 w-5" />}>
        <ol className="space-y-3">
          {DEMO.map((d, i) => (
            <li key={i} className="flex gap-4 rounded-2xl border border-slate-200 p-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-gold-300 to-gold-500 text-sm font-extrabold text-ink-900">{i + 1}</span>
              <div className="flex-1">
                <p className="text-xs font-bold uppercase tracking-wider text-royal-600">{d.who}{d.email && <span className="ml-2 font-mono normal-case tracking-normal text-slate-400">{d.email}</span>}</p>
                <p className="mt-1 text-sm text-slate-700">{d.step}</p>
              </div>
              <Link to={d.to} className="self-center text-xs font-semibold text-royal-600 hover:underline">Open →</Link>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-slate-500">All demo passwords: <span className="font-mono">Demo@123456</span> (admin: <span className="font-mono">Admin@123456</span>). Sample CPGRAMS export for the import demo: <span className="font-mono">docs/samples/cpgrams_export_sample.csv</span>.</p>
      </Card>
      <Card title="Problem statement coverage" icon={<GitMerge className="h-5 w-5" />}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {COVERAGE.map((c) => (
            <Link key={c.t} to={c.to} className="group rounded-2xl border border-slate-200 p-4 transition hover:border-royal-200 hover:shadow-soft">
              <div className="flex items-center gap-2"><c.icon className="h-4 w-4 text-royal-500" /><p className="text-sm font-bold text-slate-900">{c.t}</p><CheckCircle2 className="ml-auto h-4 w-4 text-emerald-500" /></div>
              <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{c.d}</p>
            </Link>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default function HelpPage() {
  return (
    <div>
      <PageHeader eyebrow="Help" title="Help & demo guide" description="How NYAYA SETU maps to PS 26264 and a guided walkthrough with demo accounts." />
      <HelpContent />
    </div>
  )
}
