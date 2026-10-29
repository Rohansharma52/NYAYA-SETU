import { cn } from '../../lib/cn'
import markSrc from '../../assets/nyaya-mark.png'

/**
 * NYAYA SETU mark: the team's scales-over-a-bridge logo, set on an ivory disc
 * with a thin gold-to-royal ring so the blue artwork stays legible on dark UI.
 */
export function LogoMark({ size = 36, className, glow }: { size?: number; className?: string; glow?: boolean }) {
  return (
    <span
      className={cn('logo-badge relative inline-flex shrink-0 items-center justify-center rounded-full', glow && 'logo-badge-glow', className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <img src={markSrc} alt="" draggable={false} className="h-[86%] w-[86%] select-none object-contain" />
    </span>
  )
}

export function Logo({ dark = true, compact, className }: { dark?: boolean; compact?: boolean; className?: string }) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <LogoMark size={compact ? 34 : 40} glow />
      {!compact && (
        <div className="leading-none">
          <p className={cn('font-serif text-[17px] font-bold tracking-[0.18em]', dark ? 'text-gradient-gold animate-sheen' : 'text-ink-900')}>NYAYA SETU</p>
          <p className={cn('mt-1 whitespace-nowrap text-[9.5px] font-semibold uppercase tracking-[0.16em]', dark ? 'text-royal-200/70' : 'text-slate-500')}>
            AICTE · Complaint Monitor
          </p>
        </div>
      )}
    </div>
  )
}
