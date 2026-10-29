import { Link } from 'react-router-dom'
import { ShieldX } from 'lucide-react'

export default function AccessDeniedPage() {
  return (
    <div className="bg-hero flex min-h-screen flex-col items-center justify-center p-6 text-center text-white">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-rose-500/15 ring-1 ring-rose-400/30"><ShieldX className="h-8 w-8 text-rose-300" /></span>
      <h1 className="mt-6 text-2xl font-extrabold text-white">Access restricted</h1>
      <p className="mt-2 max-w-md text-sm text-white/60">Your role does not permit this page. Access is enforced on the server as well — contact the system administrator if you need it.</p>
      <Link to="/dashboard" className="mt-8 rounded-xl bg-white/10 px-6 py-3 text-sm font-bold text-white ring-1 ring-white/20 hover:bg-white/15">Back to Command Centre</Link>
    </div>
  )
}
