import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '../../lib/cn'

interface PaginationProps {
  total: number
  skip: number
  limit: number
  onPageChange: (newSkip: number) => void
}

export function Pagination({ total, skip, limit, onPageChange }: PaginationProps) {
  const page = Math.floor(skip / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  if (total <= limit) {
    return <p className="px-1 text-xs text-slate-500">{total} record{total === 1 ? '' : 's'}</p>
  }
  const nums: (number | '…')[] = []
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - page) <= 1) nums.push(p)
    else if (nums[nums.length - 1] !== '…') nums.push('…')
  }
  return (
    <div className="flex items-center justify-between gap-3">
      <p className="text-xs text-slate-500">
        Showing <span className="font-semibold text-slate-700">{skip + 1}–{Math.min(skip + limit, total)}</span> of{' '}
        <span className="font-semibold text-slate-700">{total}</span>
      </p>
      <div className="flex items-center gap-1">
        <button
          disabled={page === 1}
          onClick={() => onPageChange(Math.max(0, skip - limit))}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-40"
          aria-label="Previous page"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        {nums.map((n, i) =>
          n === '…' ? (
            <span key={`e${i}`} className="px-1 text-xs text-slate-400">…</span>
          ) : (
            <button
              key={n}
              onClick={() => onPageChange((n - 1) * limit)}
              className={cn(
                'h-8 min-w-[32px] rounded-lg px-2 text-xs font-semibold transition',
                n === page ? 'bg-ink-900 text-white shadow-soft' : 'text-slate-600 hover:bg-slate-100',
              )}
            >
              {n}
            </button>
          ),
        )}
        <button
          disabled={page === pages}
          onClick={() => onPageChange(skip + limit)}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:bg-slate-100 disabled:opacity-40"
          aria-label="Next page"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
