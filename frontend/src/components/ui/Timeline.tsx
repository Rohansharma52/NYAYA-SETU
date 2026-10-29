import type { LucideIcon } from 'lucide-react'
import {
  ArrowLeftRight, CheckCircle2, FileText, Flag, GitMerge, Mail, PlusCircle, ShieldAlert, UserCheck, Paperclip, Sparkles, Search,
} from 'lucide-react'
import { cn } from '../../lib/cn'
import { fmtDateTime, fromNow } from '../../lib/format'
import { BureauChip } from './Badge'

export interface TimelineEvent {
  id: number | string
  type: string
  description: string
  performedBy?: string | null
  createdAt?: string | null
  bureau?: string | null
  caseNumber?: string | null
}

const ICONS: Record<string, { icon: LucideIcon; tone: string }> = {
  created: { icon: PlusCircle, tone: 'bg-slate-100 text-slate-600' },
  assigned: { icon: UserCheck, tone: 'bg-royal-50 text-royal-600' },
  status_change: { icon: Flag, tone: 'bg-indigo-50 text-indigo-600' },
  letter_issued: { icon: Mail, tone: 'bg-sky-50 text-sky-600' },
  show_cause: { icon: ShieldAlert, tone: 'bg-rose-50 text-rose-600' },
  inspection: { icon: Search, tone: 'bg-violet-50 text-violet-600' },
  transfer_requested: { icon: ArrowLeftRight, tone: 'bg-cyan-50 text-cyan-600' },
  transfer_accepted: { icon: ArrowLeftRight, tone: 'bg-cyan-50 text-cyan-700' },
  transfer_rejected: { icon: ArrowLeftRight, tone: 'bg-rose-50 text-rose-600' },
  coordination_linked: { icon: GitMerge, tone: 'bg-gold-50 text-gold-700' },
  document_attached: { icon: Paperclip, tone: 'bg-teal-50 text-teal-600' },
  identity_resolved: { icon: Sparkles, tone: 'bg-gold-50 text-gold-700' },
  note: { icon: FileText, tone: 'bg-slate-100 text-slate-600' },
  disposed: { icon: CheckCircle2, tone: 'bg-emerald-50 text-emerald-600' },
}

export function Timeline({ events, compact }: { events: TimelineEvent[]; compact?: boolean }) {
  if (!events.length) return <p className="py-8 text-center text-sm text-slate-400">No actions recorded yet.</p>
  return (
    <ol className="relative space-y-1">
      <span className="absolute bottom-3 left-[17px] top-3 w-px bg-gradient-to-b from-slate-200 via-slate-200 to-transparent" aria-hidden />
      {events.map((e, i) => {
        const meta = ICONS[e.type] ?? ICONS.note
        const Icon = meta.icon
        return (
          <li key={e.id} className="relative flex gap-3.5 rounded-xl p-1.5 transition hover:bg-slate-50" style={{ animation: `fade-up .45s var(--ease-out) ${Math.min(i, 10) * 0.04}s both` }}>
            <span className={cn('relative z-10 flex h-[34px] w-[34px] shrink-0 items-center justify-center rounded-xl ring-4 ring-white', meta.tone)}>
              <Icon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1 pb-1 pt-0.5">
              <div className="flex flex-wrap items-center gap-2">
                {e.bureau && <BureauChip code={e.bureau} />}
                {e.caseNumber && <span className="font-mono text-[11px] text-slate-400">{e.caseNumber}</span>}
              </div>
              <p className={cn('text-sm leading-snug text-slate-700', e.bureau || e.caseNumber ? 'mt-1' : '')}>{e.description}</p>
              <p className="mt-0.5 text-xs text-slate-400" title={fmtDateTime(e.createdAt)}>
                {e.performedBy && <span className="font-medium text-slate-500">{e.performedBy} · </span>}
                {compact ? fromNow(e.createdAt) : fmtDateTime(e.createdAt)}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
