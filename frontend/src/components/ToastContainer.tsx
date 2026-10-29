import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useToast, type ToastItem } from '../hooks/useToast'
import { cn } from '../lib/cn'

const META: Record<ToastItem['type'], { icon: typeof Info; tone: string; bar: string }> = {
  success: { icon: CheckCircle2, tone: 'text-emerald-500', bar: 'bg-emerald-500' },
  error: { icon: XCircle, tone: 'text-rose-500', bar: 'bg-rose-500' },
  warning: { icon: AlertTriangle, tone: 'text-amber-500', bar: 'bg-amber-500' },
  info: { icon: Info, tone: 'text-royal-500', bar: 'bg-royal-500' },
}

export function ToastContainer() {
  const { toasts, dismiss } = useToast()
  return (
    <div aria-live="polite" className="no-print pointer-events-none fixed bottom-5 right-5 z-[100] flex w-[360px] max-w-[calc(100vw-2.5rem)] flex-col gap-2">
      {toasts.map((t) => {
        const m = META[t.type]
        return (
          <div key={t.id} role="status" className="pointer-events-auto relative flex animate-slide-in-right items-start gap-3 overflow-hidden rounded-2xl border border-slate-200 bg-white px-4 py-3.5 shadow-lift">
            <span className={cn('absolute inset-y-0 left-0 w-1', m.bar)} />
            <m.icon className={cn('mt-0.5 h-5 w-5 shrink-0', m.tone)} />
            <p className="flex-1 text-sm font-medium text-slate-700">{t.message}</p>
            <button onClick={() => dismiss(t.id)} aria-label="Dismiss" className="rounded-md p-0.5 text-slate-400 hover:text-slate-700">
              <X className="h-4 w-4" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
