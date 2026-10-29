import { RefreshCw, WifiOff } from 'lucide-react'
import { Button } from './Button'

export function ErrorState({ message = 'We could not load this data. Check that the API server is running.', onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 text-rose-500 ring-1 ring-rose-100">
        <WifiOff className="h-6 w-6" />
      </div>
      <h3 className="text-base font-bold text-slate-900">Something went wrong</h3>
      <p className="mt-1 max-w-sm text-sm text-slate-500">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-5" leftIcon={<RefreshCw className="h-3.5 w-3.5" />} onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
