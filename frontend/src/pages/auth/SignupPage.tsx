import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2 } from 'lucide-react'
import { AuthLayout } from '../../components/layout/AuthLayout'
import { apiClient, apiError } from '../../api/client'

const field = 'h-11 w-full rounded-xl border border-white/10 bg-white/[.06] px-3.5 text-sm text-white placeholder:text-white/30 focus:border-gold-300/60 focus:outline-none focus:ring-4 focus:ring-gold-400/15'

export default function SignupPage() {
  const [form, setForm] = useState({ full_name: '', email: '', designation: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const up = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [k]: e.target.value }))
  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (form.password.length < 8) return setError('Password must be at least 8 characters')
    if (form.password !== form.confirm) return setError('Passwords do not match')
    setLoading(true); setError(null)
    try {
      await apiClient.post('/auth/signup', { full_name: form.full_name, email: form.email, designation: form.designation || undefined, password: form.password })
      setDone(true)
    } catch (err) { setError(apiError(err, 'Sign-up failed')) } finally { setLoading(false) }
  }
  return (
    <AuthLayout>
      <div className="glass ring-gradient rounded-3xl p-7 sm:p-8">
        {done ? (
          <div className="py-6 text-center">
            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
            <h1 className="mt-4 text-xl font-extrabold text-white">Request submitted</h1>
            <p className="mt-2 text-sm text-white/60">A system administrator will verify your role and bureau before activating the account.</p>
            <Link to="/login" className="mt-6 inline-block text-sm font-semibold text-gold-300">Back to sign in →</Link>
          </div>
        ) : (
          <>
            <h1 className="text-[24px] font-extrabold text-white">Request access</h1>
            <p className="mt-1 text-sm text-white/55">For AICTE officials. Accounts are activated after verification.</p>
            <form onSubmit={submit} className="mt-6 space-y-3.5">
              <input className={field} placeholder="Full name" value={form.full_name} onChange={up('full_name')} required />
              <input className={field} type="email" placeholder="Official e-mail" value={form.email} onChange={up('email')} required />
              <input className={field} placeholder="Designation (optional)" value={form.designation} onChange={up('designation')} />
              <div className="grid grid-cols-2 gap-3">
                <input className={field} type="password" placeholder="Password" value={form.password} onChange={up('password')} required />
                <input className={field} type="password" placeholder="Confirm" value={form.confirm} onChange={up('confirm')} required />
              </div>
              {error && <p className="rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-[13px] text-rose-200">{error}</p>}
              <button disabled={loading} className="h-12 w-full rounded-xl bg-gradient-to-r from-gold-300 via-gold-400 to-gold-500 font-bold text-ink-900 shadow-glow-gold transition hover:brightness-105 disabled:opacity-60">{loading ? 'Submitting…' : 'Submit request'}</button>
            </form>
            <p className="mt-6 text-center text-[13px] text-white/45">Already have access? <Link to="/login" className="font-semibold text-gold-300">Sign in</Link></p>
          </>
        )}
      </div>
    </AuthLayout>
  )
}
