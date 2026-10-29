import { FlaskConical } from 'lucide-react'

export function DataNote({ message = 'Demo data — synthetic records for the SIH prototype. Not official AICTE data.' }: { message?: string }) {
  return (
    <p className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
      <FlaskConical className="h-3 w-3" />
      {message}
    </p>
  )
}
