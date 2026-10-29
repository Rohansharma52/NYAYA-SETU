import { cn } from '../../lib/cn'

export function SkeletonLine({ width = '100%', height = '12px', className }: { width?: string; height?: string; className?: string }) {
  return <div className={cn('skeleton', className)} style={{ width, height }} />
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('card space-y-3 p-5', className)}>
      <SkeletonLine width="40%" height="10px" />
      <SkeletonLine width="60%" height="26px" />
      <SkeletonLine width="80%" height="10px" />
    </div>
  )
}

export function TableSkeleton({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-3 p-5">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="grid gap-4" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
          {Array.from({ length: cols }).map((__, c) => (
            <SkeletonLine key={c} width={c === 0 ? '70%' : `${50 + ((r * 7 + c * 13) % 45)}%`} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonLine width="260px" height="28px" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
      <div className="card"><TableSkeleton /></div>
    </div>
  )
}
