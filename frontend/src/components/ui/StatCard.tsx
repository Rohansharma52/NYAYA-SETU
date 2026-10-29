import React from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { cn } from '../../lib/cn'
import { AnimatedNumber, Sparkline } from './Visuals'

interface StatCardProps {
  label: string
  value: number
  icon: React.ReactNode
  accent?: 'royal' | 'gold' | 'rose' | 'emerald' | 'cyan' | 'violet' | 'slate' | 'orange'
  hint?: React.ReactNode
  trend?: number[]
  to?: string
  suffix?: string
  decimals?: number
}

const ACCENTS = {
  royal: { icon: 'bg-royal-50 text-royal-600 ring-royal-100', line: '#5B66EC' },
  gold: { icon: 'bg-gold-50 text-gold-600 ring-gold-100', line: '#EC960B' },
  rose: { icon: 'bg-rose-50 text-rose-600 ring-rose-100', line: '#E11D48' },
  emerald: { icon: 'bg-emerald-50 text-emerald-600 ring-emerald-100', line: '#059669' },
  cyan: { icon: 'bg-cyan-50 text-cyan-600 ring-cyan-100', line: '#0891B2' },
  violet: { icon: 'bg-violet-50 text-violet-600 ring-violet-100', line: '#7C3AED' },
  slate: { icon: 'bg-slate-100 text-slate-600 ring-slate-200', line: '#64748B' },
  orange: { icon: 'bg-orange-50 text-orange-600 ring-orange-100', line: '#EA580C' },
}

export function StatCard({ label, value, icon, accent = 'royal', hint, trend, to, suffix, decimals }: StatCardProps) {
  const a = ACCENTS[accent]
  const body = (
    <div className="card card-hover group relative h-full overflow-hidden p-4">
      <div className="flex items-start justify-between gap-3">
        <div className={cn('flex h-10 w-10 items-center justify-center rounded-xl ring-1', a.icon)}>{icon}</div>
        {to && <ArrowUpRight className="h-4 w-4 text-slate-300 transition group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-slate-500" />}
      </div>
      <p className="mt-3 text-[12.5px] font-semibold text-slate-500">{label}</p>
      <p className="mt-0.5 text-[28px] font-extrabold leading-tight tracking-tight text-slate-900">
        <AnimatedNumber value={value} suffix={suffix} decimals={decimals} />
      </p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
      {trend && trend.length > 1 && (
        <div className="-mx-4 -mb-4 mt-2 opacity-90">
          <Sparkline data={trend} color={a.line} height={34} />
        </div>
      )}
    </div>
  )
  return to ? <Link to={to} className="block h-full">{body}</Link> : body
}
