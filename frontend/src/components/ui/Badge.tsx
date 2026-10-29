import React from 'react'
import { cn } from '../../lib/cn'
import { STATUS_META, SEVERITY_META, CLASSIFICATION_META, RISK_META, bureauStyle } from '../../lib/domain'
import { titleCase } from '../../lib/format'

export type BadgeColor = 'gray' | 'blue' | 'indigo' | 'yellow' | 'orange' | 'purple' | 'green' | 'red' | 'cyan' | 'gold'
export type BadgeSize = 'sm' | 'md'

const COLORS: Record<BadgeColor, string> = {
  gray: 'bg-slate-50 text-slate-700 border-slate-200',
  blue: 'bg-sky-50 text-sky-700 border-sky-200',
  indigo: 'bg-royal-50 text-royal-700 border-royal-200',
  yellow: 'bg-amber-50 text-amber-700 border-amber-200',
  orange: 'bg-orange-50 text-orange-700 border-orange-200',
  purple: 'bg-violet-50 text-violet-700 border-violet-200',
  green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  red: 'bg-rose-50 text-rose-700 border-rose-200',
  cyan: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  gold: 'bg-gold-50 text-gold-700 border-gold-200',
}

export function Badge({
  color = 'gray',
  size = 'sm',
  children,
  className,
  icon,
}: {
  color?: BadgeColor
  size?: BadgeSize
  children: React.ReactNode
  className?: string
  icon?: React.ReactNode
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border font-semibold',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        COLORS[color],
        className,
      )}
    >
      {icon}
      {children}
    </span>
  )
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const meta = STATUS_META[status]
  return (
    <span className={cn('chip whitespace-nowrap', meta?.chip ?? 'bg-slate-50 text-slate-600 border-slate-200', className)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', meta?.dot ?? 'bg-slate-400')} />
      {meta?.label ?? titleCase(status)}
    </span>
  )
}

const PRIORITY: Record<string, string> = {
  low: 'text-slate-500',
  medium: 'text-sky-600',
  high: 'text-orange-600',
  urgent: 'text-rose-600',
}

export function PriorityBadge({ priority }: { priority: string }) {
  const bars = { low: 1, medium: 2, high: 3, urgent: 4 }[priority] ?? 1
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-semibold', PRIORITY[priority] ?? 'text-slate-500')}>
      <span className="flex items-end gap-[2px]" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={cn('w-[3px] rounded-sm', i <= bars ? 'bg-current' : 'bg-slate-200')}
            style={{ height: 4 + i * 2 }}
          />
        ))}
      </span>
      {titleCase(priority)}
    </span>
  )
}

export function BureauChip({ code, name, className, solid }: { code?: string | null; name?: boolean; className?: string; solid?: boolean }) {
  const s = bureauStyle(code)
  return (
    <span
      title={s.name}
      className={cn('chip whitespace-nowrap font-bold tracking-wide', className)}
      style={
        solid
          ? { background: s.color, color: '#fff', borderColor: s.color }
          : { background: `${s.color}12`, color: s.color, borderColor: `${s.color}40` }
      }
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: solid ? '#fff' : s.color }} />
      {s.code}
      {name && <span className="font-medium opacity-80">· {s.name}</span>}
    </span>
  )
}

export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  const m = SEVERITY_META[severity] ?? SEVERITY_META.none
  return (
    <span className={cn('chip', m.chip, className)}>
      <span className={cn('h-1.5 w-1.5 rounded-full', m.dot, severity === 'critical' && 'animate-blink')} />
      {m.label}
    </span>
  )
}

export function ClassificationBadge({ value }: { value: string }) {
  const m = CLASSIFICATION_META[value]
  return <span className={cn('chip', m?.chip ?? 'bg-slate-50 text-slate-600 border-slate-200')}>{m?.label ?? titleCase(value)}</span>
}

export function RiskBadge({ level }: { level: string }) {
  const m = RISK_META[level] ?? RISK_META.low
  return (
    <span className={cn('chip', m.chip)}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
      {m.label}
    </span>
  )
}
