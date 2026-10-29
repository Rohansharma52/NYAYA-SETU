import React, { useEffect, useRef, useState } from 'react'
import { cn } from '../../lib/cn'
import { initials } from '../../lib/format'

/** Count-up number that animates when the value changes. */
export function AnimatedNumber({ value, duration = 900, decimals = 0, suffix = '' }: { value: number; duration?: number; decimals?: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  const from = useRef(0)
  useEffect(() => {
    const start = performance.now()
    const initial = from.current
    let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration)
      const eased = 1 - Math.pow(1 - p, 4)
      setDisplay(initial + (value - initial) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = value
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [value, duration])
  return (
    <span className="tabular">
      {display.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  )
}

export function Sparkline({ data, color = '#5B66EC', height = 36, className }: { data: number[]; color?: string; height?: number; className?: string }) {
  const id = React.useId().replace(/:/g, '')
  if (!data.length) return null
  const w = 120
  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const pts = data.map((v, i) => [(i / Math.max(data.length - 1, 1)) * w, height - ((v - min) / (max - min || 1)) * (height - 6) - 3])
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className={cn('w-full', className)} style={{ height }} preserveAspectRatio="none" aria-hidden>
      <defs>
        <linearGradient id={`sg${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity=".28" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${d} L${w},${height} L0,${height} Z`} fill={`url(#sg${id})`} />
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1" strokeDashoffset="1" className="animate-draw" />
    </svg>
  )
}

export function ScoreRing({ value, size = 88, stroke = 8, color = '#5B66EC', track = '#E8EBF6', label, sublabel, max = 100 }: {
  value: number; size?: number; stroke?: number; color?: string; track?: string; label?: React.ReactNode; sublabel?: React.ReactNode; max?: number
}) {
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const [p, setP] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setP(Math.max(0, Math.min(1, value / max))), 60)
    return () => clearTimeout(t)
  }, [value, max])
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - p)} style={{ transition: 'stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-lg font-extrabold leading-none text-slate-900 tabular">{label ?? Math.round(value)}</span>
        {sublabel && <span className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{sublabel}</span>}
      </div>
    </div>
  )
}

export function Meter({ value, max = 100, className, barClassName, color }: { value: number; max?: number; className?: string; barClassName?: string; color?: string }) {
  const [w, setW] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setW(Math.max(0, Math.min(100, (value / (max || 1)) * 100))), 50)
    return () => clearTimeout(t)
  }, [value, max])
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-slate-100', className)}>
      <div
        className={cn('h-full rounded-full bg-gradient-to-r from-royal-500 to-royal-400', barClassName)}
        style={{ width: `${w}%`, transition: 'width 1s cubic-bezier(.22,1,.36,1)', ...(color ? { background: color } : {}) }}
      />
    </div>
  )
}

const AVATAR_TONES = ['from-royal-500 to-violet-500', 'from-gold-400 to-orange-500', 'from-teal-500 to-emerald-500', 'from-pink-500 to-rose-500', 'from-sky-500 to-indigo-500']

export function Avatar({ name, size = 32, className }: { name?: string | null; size?: number; className?: string }) {
  const tone = AVATAR_TONES[(name ?? '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_TONES.length]
  return (
    <span
      className={cn('inline-flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-bold text-white ring-2 ring-white', tone, className)}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
      title={name ?? undefined}
    >
      {initials(name)}
    </span>
  )
}

export function LiveDot({ className, color = 'bg-emerald-400' }: { className?: string; color?: string }) {
  return (
    <span className={cn('relative inline-flex h-2 w-2', className)}>
      <span className={cn('absolute inline-flex h-full w-full animate-pulse-ring rounded-full', color)} />
      <span className={cn('relative inline-flex h-2 w-2 rounded-full', color)} />
    </span>
  )
}

export function Segmented<T extends string>({ value, onChange, options, className }: { value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; className?: string }) {
  return (
    <div className={cn('inline-flex rounded-xl bg-slate-100/80 p-1', className)}>
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'rounded-lg px-3 py-1.5 text-xs font-semibold transition-all',
            value === o.value ? 'bg-white text-slate-900 shadow-soft' : 'text-slate-500 hover:text-slate-800',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Fades children in when they scroll into view. */
export function Reveal({ children, className, delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        setShown(true)
        io.disconnect()
      }
    }, { threshold: 0.12 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: shown ? 1 : 0,
        transform: shown ? 'none' : 'translateY(14px)',
        transition: `opacity .6s var(--ease-out) ${delay}s, transform .6s var(--ease-out) ${delay}s`,
      }}
    >
      {children}
    </div>
  )
}
