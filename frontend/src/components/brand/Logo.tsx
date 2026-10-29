import { cn } from '../../lib/cn'

/** Abstract "bridge of justice" mark: a span of pillars under an arc with a rising sun. */
export function LogoMark({ size = 36, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" className={className} aria-hidden>
      <defs>
        <linearGradient id="lm-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FDE08A" />
          <stop offset="1" stopColor="#EC960B" />
        </linearGradient>
        <linearGradient id="lm-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#1A2756" />
          <stop offset="1" stopColor="#0A1029" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#lm-bg)" />
      <rect x="0.5" y="0.5" width="63" height="63" rx="15.5" fill="none" stroke="rgba(255,255,255,.12)" />
      <path d="M12 44c6-11 13-16 20-16s14 5 20 16" fill="none" stroke="url(#lm-g)" strokeWidth="3.6" strokeLinecap="round" />
      <path d="M10 44.5h44" stroke="#7C88F5" strokeWidth="3.6" strokeLinecap="round" />
      <circle cx="32" cy="18" r="5" fill="url(#lm-g)" />
      <path d="M19 44v-6M25.5 44V33.5M32 44V30M38.5 44v-10.5M45 44v-6" stroke="#C7CFFE" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  )
}

export function Logo({ dark = true, compact, className }: { dark?: boolean; compact?: boolean; className?: string }) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <LogoMark size={compact ? 32 : 38} />
      {!compact && (
        <div className="leading-none">
          <p className={cn('font-serif text-[17px] font-bold tracking-[0.18em]', dark ? 'text-gradient-gold' : 'text-ink-900')}>NYAYA SETU</p>
          <p className={cn('mt-1 whitespace-nowrap text-[9.5px] font-semibold uppercase tracking-[0.16em]', dark ? 'text-royal-200/70' : 'text-slate-500')}>
            AICTE · Complaint Monitor
          </p>
        </div>
      )}
    </div>
  )
}
