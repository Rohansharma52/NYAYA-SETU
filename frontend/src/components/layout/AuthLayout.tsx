import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Fingerprint, GitMerge, BellRing, ShieldCheck } from 'lucide-react'
import { ParticleWordmark } from '../brand/ParticleWordmark'
import { LogoMark } from '../brand/Logo'
import { cn } from '../../lib/cn'

const PILLARS = [
  { icon: Fingerprint, title: 'Identity Resolution', text: 'Finds the institution even from acronyms, typos or Hindi' },
  { icon: GitMerge, title: 'Overlap & Conflict Intelligence', text: 'Flags RB · PGRC parallel or contradictory action' },
  { icon: BellRing, title: 'Timeline Alerts', text: 'Pending, escalation and SLA alerts across bureaus' },
]

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const [assembled, setAssembled] = useState(false)
  return (
    <div className="relative min-h-screen overflow-hidden bg-ink-950 text-white">
      {/* Atmosphere */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute inset-0 bg-grid opacity-[.35] [mask-image:radial-gradient(ellipse_at_center,#000_30%,transparent_75%)]" />
        <div className="absolute -left-40 top-[-10%] h-[520px] w-[520px] rounded-full bg-royal-600/25 blur-[120px] animate-float" />
        <div className="absolute bottom-[-20%] right-[-10%] h-[560px] w-[560px] rounded-full bg-gold-500/15 blur-[130px] animate-float [animation-delay:-3s]" />
        <div className="absolute left-1/3 top-1/2 h-[380px] w-[380px] rounded-full bg-violet-600/10 blur-[110px]" />
      </div>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-[1.25fr_1fr]">
        {/* Brand panel */}
        <section className="flex flex-col justify-between px-6 pb-6 pt-8 sm:px-10 lg:px-14 lg:py-10">
          <header className="flex items-center gap-3 animate-fade-in">
            <LogoMark size={34} />
            <div className="leading-tight">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-royal-200/70">All India Council for Technical Education</p>
              <p className="text-[11px] text-white/40">Smart India Hackathon · PS 26264 · Regulation Bureau</p>
            </div>
          </header>

          <div className="my-8 lg:my-0">
            <div className="relative mx-auto w-full max-w-[760px]">
              <ParticleWordmark className="h-[120px] w-full sm:h-[170px] lg:h-[210px]" onAssembled={() => setAssembled(true)} />
              {/* Setu — the bridge */}
              <svg viewBox="0 0 760 60" className="-mt-2 h-10 w-full sm:h-12" preserveAspectRatio="none" aria-hidden>
                <defs>
                  <linearGradient id="bridge" x1="0" x2="1">
                    <stop offset="0" stopColor="#F8B424" stopOpacity="0" />
                    <stop offset=".5" stopColor="#FCCB4D" stopOpacity=".9" />
                    <stop offset="1" stopColor="#F8B424" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path
                  d="M20 52 Q380 -18 740 52"
                  fill="none"
                  stroke="url(#bridge)"
                  strokeWidth="1.6"
                  pathLength={1}
                  strokeDasharray="1"
                  strokeDashoffset="1"
                  className={cn(assembled && 'animate-draw')}
                />
                {[0.12, 0.26, 0.4, 0.5, 0.6, 0.74, 0.88].map((p, i) => {
                  const x = 20 + 720 * p
                  const y = 52 - 70 * 4 * p * (1 - p) * 0.5
                  return (
                    <line
                      key={i}
                      x1={x} x2={x} y1={y + 2} y2={52}
                      stroke="#7C88F5" strokeOpacity=".45" strokeWidth="1"
                      style={{ opacity: assembled ? 1 : 0, transition: `opacity .6s ease ${0.6 + i * 0.08}s` }}
                    />
                  )
                })}
              </svg>
              <div className={cn('mt-3 text-center transition-all duration-1000', assembled ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0')}>
                <p className="font-deva text-2xl font-semibold tracking-wide text-gold-200/90 sm:text-[28px]">न्याय सेतु</p>
                <p className="mt-3 text-sm font-medium text-royal-100/80 sm:text-base">
                  One institution · One record · <span className="text-gold-300">One voice</span>
                </p>
              </div>
            </div>

            <div className={cn('mx-auto mt-10 hidden max-w-[760px] gap-3 transition-all duration-1000 sm:grid sm:grid-cols-3', assembled ? 'opacity-100' : 'opacity-0')}>
              {PILLARS.map((p, i) => (
                <div
                  key={p.title}
                  className="glass rounded-2xl p-4"
                  style={{ transition: `transform .8s var(--ease-out) ${0.2 + i * 0.12}s, opacity .8s ease ${0.2 + i * 0.12}s`, transform: assembled ? 'none' : 'translateY(12px)', opacity: assembled ? 1 : 0 }}
                >
                  <p.icon className="h-5 w-5 text-gold-300" />
                  <p className="mt-3 text-[13px] font-bold text-white">{p.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-white/55">{p.text}</p>
                </div>
              ))}
            </div>
          </div>

          <footer className="hidden items-center gap-2 text-[11px] text-white/35 lg:flex">
            <ShieldCheck className="h-3.5 w-3.5" />
            Prototype with synthetic demo data · Every match is advisory — officers decide · No complaint data leaves AICTE servers
          </footer>
        </section>

        {/* Form panel */}
        <section className="flex items-center justify-center px-5 pb-10 sm:px-8 lg:py-10">
          <div className="w-full max-w-[440px] animate-slide-in-right [animation-delay:.35s]">{children}</div>
        </section>
      </div>

      <Link to="/signup" className="absolute right-5 top-5 z-20 hidden text-xs font-semibold text-white/50 transition hover:text-white lg:block">
        Request access →
      </Link>
    </div>
  )
}
