import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Lock, Mail, Sparkles } from 'lucide-react'
import { AuthLayout } from '../../components/layout/AuthLayout'
import { useAuth } from '../../contexts/AuthContext'
import { cn } from '../../lib/cn'

const DEMO_ACCOUNTS = [
  { label: 'Management', sub: 'Director, Monitoring', email: 'management@aicte.demo', password: 'Demo@123456', tone: 'from-gold-400 to-orange-500' },
  { label: 'RB Officer', sub: 'Regulation Bureau', email: 'officer1@aicte.demo', password: 'Demo@123456', tone: 'from-royal-500 to-indigo-600' },
  { label: 'PGRC Officer', sub: 'Grievance Cell', email: 'officer2@aicte.demo', password: 'Demo@123456', tone: 'from-amber-500 to-gold-600' },
  { label: 'Reviewer', sub: 'Coordination', email: 'reviewer@aicte.demo', password: 'Demo@123456', tone: 'from-teal-500 to-emerald-600' },
  { label: 'Admin', sub: 'System', email: 'admin@aicte.demo', password: 'Admin@123456', tone: 'from-violet-500 to-fuchsia-600' },
]

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  async function submit(e?: React.FormEvent, creds?: { email: string; password: string }) {
    e?.preventDefault()
    const em = creds?.email ?? email
    const pw = creds?.password ?? password
    if (!em || !pw) {
      setError('Enter your official e-mail and password')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await login(em, pw)
      navigate('/dashboard', { replace: true })
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Unable to reach the NYAYA SETU server. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="glass ring-gradient rounded-3xl p-7 shadow-[0_30px_80px_-30px_rgba(0,0,0,.7)] sm:p-8">
        <div className="mb-7">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-gold-400/10 px-2.5 py-1 text-[11px] font-semibold text-gold-300 ring-1 ring-gold-400/25">
            <Sparkles className="h-3 w-3" /> Single-window monitoring
          </span>
          <h1 className="mt-4 text-[26px] font-extrabold leading-tight text-white">Sign in to the command centre</h1>
          <p className="mt-1.5 text-sm text-white/55">Authorised AICTE officials only. Activity is audit-logged.</p>
        </div>

        <form onSubmit={submit} className="space-y-4" noValidate>
          <label className="block">
            <span className="mb-1.5 block text-[12.5px] font-semibold text-white/70">Official e-mail</span>
            <span className="relative block">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35" />
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@aicte.gov.in"
                className="h-12 w-full rounded-xl border border-white/10 bg-white/[.06] pl-10 pr-3 text-sm text-white placeholder:text-white/30 transition focus:border-gold-300/60 focus:bg-white/[.09] focus:outline-none focus:ring-4 focus:ring-gold-400/15"
              />
            </span>
          </label>
          <label className="block">
            <span className="mb-1.5 flex items-center justify-between text-[12.5px] font-semibold text-white/70">
              Password
              <span title="Contact the system administrator to reset" className="cursor-help text-[11.5px] font-medium text-white/40">Forgot? Contact admin</span>
            </span>
            <span className="relative block">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-white/35" />
              <input
                type={show ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••"
                className="h-12 w-full rounded-xl border border-white/10 bg-white/[.06] pl-10 pr-11 text-sm text-white placeholder:text-white/30 transition focus:border-gold-300/60 focus:bg-white/[.09] focus:outline-none focus:ring-4 focus:ring-gold-400/15"
              />
              <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-white/40 hover:text-white">
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </span>
          </label>

          {error && (
            <p role="alert" className="animate-fade-in rounded-xl border border-rose-400/25 bg-rose-500/10 px-3.5 py-2.5 text-[13px] text-rose-200">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="group relative flex h-12 w-full items-center justify-center gap-2 overflow-hidden rounded-xl bg-gradient-to-r from-gold-300 via-gold-400 to-gold-500 text-[15px] font-bold text-ink-900 shadow-glow-gold transition hover:brightness-105 active:translate-y-px disabled:opacity-60"
          >
            <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/45 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
            {loading ? (
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-ink-900/30 border-t-ink-900" />
            ) : (
              <>
                Sign in <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
              </>
            )}
          </button>
        </form>

        <div className="mt-7">
          <div className="flex items-center gap-3">
            <span className="h-px flex-1 bg-white/10" />
            <span className="text-[10.5px] font-semibold uppercase tracking-[0.18em] text-white/35">One-click demo roles</span>
            <span className="h-px flex-1 bg-white/10" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.email}
                type="button"
                disabled={loading}
                onClick={() => {
                  setEmail(a.email)
                  setPassword(a.password)
                  submit(undefined, a)
                }}
                className={cn(
                  'group flex items-center gap-2 rounded-xl border border-white/10 bg-white/[.04] p-2 text-left transition hover:border-white/25 hover:bg-white/[.08] disabled:opacity-50',
                )}
              >
                <span className={cn('h-7 w-1.5 shrink-0 rounded-full bg-gradient-to-b', a.tone)} />
                <span className="min-w-0">
                  <span className="block truncate text-[12px] font-bold text-white/90">{a.label}</span>
                  <span className="block truncate text-[10.5px] text-white/40">{a.sub}</span>
                </span>
              </button>
            ))}
          </div>
        </div>

        <p className="mt-7 text-center text-[13px] text-white/45">
          New officer?{' '}
          <Link to="/signup" className="font-semibold text-gold-300 hover:text-gold-200">Request access</Link>
        </p>
      </div>
    </AuthLayout>
  )
}
