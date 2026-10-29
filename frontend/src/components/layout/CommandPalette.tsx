import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Building2, CornerDownLeft, FileText, Search, Sparkles } from 'lucide-react'
import { listCases } from '../../api/cases'
import { listInstitutions } from '../../api/institutions'
import { useDebounce } from '../../hooks/useData'
import { cn } from '../../lib/cn'
import { StatusBadge, BureauChip } from '../ui'
import { NAV_ITEMS } from './nav'

interface Item {
  id: string
  group: string
  label: string
  sub?: string
  to: string
  icon: React.ReactNode
  right?: React.ReactNode
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)
  const dq = useDebounce(q.trim(), 220)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setQ('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  const casesQ = useQuery({
    queryKey: ['palette-cases', dq],
    queryFn: () => listCases({ search: dq, limit: 6 }),
    enabled: open && dq.length >= 2,
  })
  const instQ = useQuery({
    queryKey: ['palette-inst', dq],
    queryFn: () => listInstitutions({ search: dq, limit: 5 }),
    enabled: open && dq.length >= 2,
  })

  const items: Item[] = useMemo(() => {
    const low = dq.toLowerCase()
    const pages = NAV_ITEMS.filter((n) => !low || n.label.toLowerCase().includes(low)).slice(0, low ? 4 : 7).map((n) => ({
      id: `p-${n.to}`, group: 'Go to', label: n.label, sub: n.hint, to: n.to,
      icon: <n.icon className="h-4 w-4" />,
    }))
    const insts = (instQ.data?.items ?? []).map((i) => ({
      id: `i-${i.id}`, group: 'Institutions', label: i.canonical_name,
      sub: [i.short_name, i.city, i.region].filter(Boolean).join(' · '), to: `/institutions/${i.id}`,
      icon: <Building2 className="h-4 w-4" />,
    }))
    const cases = (casesQ.data?.items ?? []).map((c) => ({
      id: `c-${c.id}`, group: 'Cases', label: c.title, sub: `${c.case_number} · ${c.institution?.canonical_name ?? ''}`,
      to: `/cases/${c.id}`, icon: <FileText className="h-4 w-4" />,
      right: <span className="flex items-center gap-1.5"><BureauChip code={c.bureau?.code} /><StatusBadge status={c.status} /></span>,
    }))
    const resolve = dq.length >= 3
      ? [{ id: 'resolve', group: 'Intelligence', label: `Identify institution in “${dq}”`, sub: 'Run the identity-resolution engine', to: `/identity-lab?q=${encodeURIComponent(dq)}`, icon: <Sparkles className="h-4 w-4" /> }]
      : []
    return [...cases, ...insts, ...resolve, ...pages]
  }, [dq, casesQ.data, instQ.data])

  useEffect(() => setActive(0), [dq])

  function go(item?: Item) {
    if (!item) return
    onClose()
    navigate(item.to)
  }

  if (!open) return null
  let lastGroup = ''
  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-start justify-center p-4 pt-[12vh]" role="dialog" aria-modal="true">
      <div className="absolute inset-0 animate-fade-in bg-ink-950/50 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative w-full max-w-2xl animate-scale-in overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lift">
        <div className="flex items-center gap-3 border-b border-slate-100 px-4">
          <Search className="h-5 w-5 text-slate-400" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') onClose()
              if (e.key === 'ArrowDown') { e.preventDefault(); setActive((a) => Math.min(a + 1, items.length - 1)) }
              if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
              if (e.key === 'Enter') go(items[active])
            }}
            placeholder="Search cases, institutions, AICTE ID, CPGRAMS ref… or jump to a page"
            className="h-14 flex-1 bg-transparent text-[15px] text-slate-800 placeholder:text-slate-400 focus:outline-none"
          />
          <span className="kbd">ESC</span>
        </div>
        <div className="max-h-[56vh] overflow-y-auto p-2">
          {items.length === 0 && (
            <p className="px-3 py-10 text-center text-sm text-slate-400">
              {casesQ.isFetching || instQ.isFetching ? 'Searching…' : 'No matches. Try a case number, institution or acronym.'}
            </p>
          )}
          {items.map((it, idx) => {
            const header = it.group !== lastGroup ? it.group : null
            lastGroup = it.group
            return (
              <div key={it.id}>
                {header && <p className="px-3 pb-1 pt-3 text-[10.5px] font-bold uppercase tracking-[0.14em] text-slate-400">{header}</p>}
                <button
                  onMouseEnter={() => setActive(idx)}
                  onClick={() => go(it)}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition',
                    idx === active ? 'bg-royal-50 text-royal-900' : 'text-slate-700',
                  )}
                >
                  <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg', idx === active ? 'bg-white text-royal-600 shadow-soft' : 'bg-slate-100 text-slate-500')}>
                    {it.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold">{it.label}</span>
                    {it.sub && <span className="block truncate text-xs text-slate-500">{it.sub}</span>}
                  </span>
                  {it.right}
                  {idx === active ? <CornerDownLeft className="h-4 w-4 text-royal-400" /> : <ArrowRight className="h-4 w-4 text-slate-300" />}
                </button>
              </div>
            )
          })}
        </div>
        <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50/70 px-4 py-2.5 text-[11px] text-slate-500">
          <span className="flex items-center gap-2"><span className="kbd">↑</span><span className="kbd">↓</span> navigate <span className="kbd">↵</span> open</span>
          <span>Search spans every Bureau / Cell</span>
        </div>
      </div>
    </div>,
    document.body,
  )
}
