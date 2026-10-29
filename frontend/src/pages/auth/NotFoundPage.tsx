import { Link } from 'react-router-dom'
import { LogoMark } from '../../components/brand/Logo'

export default function NotFoundPage() {
  return (
    <div className="bg-hero flex min-h-screen flex-col items-center justify-center p-6 text-center text-white">
      <LogoMark size={56} />
      <p className="mt-8 font-serif text-7xl font-bold text-gradient-gold">404</p>
      <h1 className="mt-3 text-2xl font-extrabold text-white">This page has crossed the bridge</h1>
      <p className="mt-2 max-w-md text-sm text-white/60">The page you are looking for does not exist or has moved.</p>
      <Link to="/dashboard" className="mt-8 rounded-xl bg-gradient-to-r from-gold-300 to-gold-500 px-6 py-3 text-sm font-bold text-ink-900">Back to Command Centre</Link>
    </div>
  )
}
