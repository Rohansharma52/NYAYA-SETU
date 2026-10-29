import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Fingerprint, GitMerge, BellRing, ShieldCheck } from 'lucide-react'
import { ParticleWordmark } from '../brand/ParticleWordmark'
import { ConstellationField } from '../brand/ConstellationField'
import { LogoMark } from '../brand/Logo'
import { cn } from '../../lib/cn'

const PILLARS = [
  { icon: Fingerprint, title: 'Identity Resolution', text: 'Finds the institution even from acronyms, typos or Hindi' },
  { icon: GitMerge, title: 'Overlap & Conflict Intelligence', text: 'Flags RB · PGRC parallel or contradictory action' },
  { icon: BellRing, title: 'Timeline Alerts', text: 'Pending, escalation and SLA alerts across bureaus' },
]

/** Track the cursor inside an element so .spotlight can light the spot under it. */
export function trackSpotlight(e: React.PointerEvent<HTMLElement>) {
  const r = e.currentTarget.getBoundingClientRect()
  e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
  e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
}

/** Logo on a stage: halo pulses, two orbit rings turn in opposite directions. */
function EmblemStage({ show }: { show: boolean }) {
  return (
    <div className={cn('relative mx-auto h-[132px] w-[132px] transition-all duration-1000 sm:h-[150px] sm:w-[150px]', show ? 'scale-100 opacity-100' : 'scale-90 opacity-0')}>
      <span className="absolute inset-[18%] rounded-full bg-gold-400/30 blur-xl" />
      <span className="animate-halo absolute inset-[16%] rounded-full border border-gold-300/50" />
      <span className="animate-halo absolute inset-[16%] rounded-full border border-royal-300/40 [animation-delay:1.6s]" />
      <svg viewBox="0 0 200 200" className="absolute inset-0 h-full w-full" aria-hidden>
        <defs>
          <linearGradient id="orbit-a" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#FDE08A" />
            <stop offset="1" stopColor="#EC960B" stopOpacity=".2" />
          </linearGradient>
          <linearGradient id="orbit-b" x1="1" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#A3AEFB" />
            <stop offset="1" stopColor="#5B66EC" stopOpacity=".15" />
          </linearGradient>
        </defs>
        <g className="orbit">
          <circle cx="100" cy="100" r="92" fill="none" stroke="url(#orbit-a)" strokeWidth="1.2" strokeDasharray="2 7" />
          <circle cx="100" cy="8" r="3.2" fill="#FDE08A" />
        </g>
        <g className="orbit-rev">
          <circle cx="100" cy="100" r="80" fill="none" stroke="url(#orbit-b)" strokeWidth="1" strokeDasharray="40 14 4 14" />
          <circle cx="180" cy="100" r="2.6" fill="#A3AEFB" />
        </g>
      </svg>
      <div className="absolute inset-[22%] flex items-center justify-center">
        <LogoMark size={86} className="!h-full !w-full" glow />
      </div>
    </div>
  )
}

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const [assembled, setAssembled] = useState(false)
  return (
    <div className="relative min-h-screen overflow-hidden bg-ink-950 text-white">
      {/* Atmosphere: tricolour aurora, light rays, connected-node field, grid, vignette */}
      <div className="pointer-events-none absolute inset-0">
        <div className="light-rays absolute -top-1/4 left-0 right-0 h-[120%] origin-top" />
        <div className="absolute -left-48 -top-40 h-[560px] w-[560px] rounded-full bg-[#FF9933]/[.14] blur-[130px] animate-float" />
        <div className="absolute left-[30%] top-[18%] h-[420px] w-[420px] rounded-full bg-royal-600/20 blur-[120px]" />
        <div className="absolute -bottom-48 right-[-8%] h-[600px] w-[600px] rounded-full bg-[#138808]/[.13] blur-[140px] animate-float [animation-delay:-3s]" />
        <div className="absolute bottom-[-10%] left-[20%] h-[380px] w-[380px] rounded-full bg-gold-500/10 blur-[120px]" />
        <div className="absolute inset-0 bg-grid opacity-[.28] [mask-image:radial-gradient(ellipse_at_center,#000_25%,transparent_72%)]" />
        <ConstellationField className="absolute inset-0 h-full w-full" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_55%,rgba(4,7,20,.75)_100%)]" />
      </div>

      <div className="relative z-10 grid min-h-screen lg:grid-cols-[1.25fr_1fr]">
        {/* Brand panel */}
        <section className="flex flex-col justify-between px-6 pb-6 pt-8 sm:px-10 lg:px-14 lg:py-10">
          <header className="flex items-center gap-3 animate-fade-in">
            <LogoMark size={42} glow />
            <div className="leading-tight">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-royal-100/80">All India Council for Technical Education</p>
              <p className="text-[11px] text-white/45">Smart India Hackathon 2026 · PS 26264 · Prototype</p>
            </div>
          </header>

          <div className="my-6 lg:my-0">
            <div className="relative mx-auto w-full max-w-[760px]">
              <EmblemStage show />
              <ParticleWordmark className="-mt-1 h-[110px] w-full sm:h-[150px] lg:h-[180px]" onAssembled={() => setAssembled(true)} />
              {/* Setu — the bridge */}
              <svg viewBox="0 0 760 60" className="-mt-2 h-10 w-full sm:h-12" preserveAspectRatio="none" aria-hidden>
                <defs>
                  <linearGradient id="bridge" x1="0" x2="1">
                    <stop offset="0" stopColor="#F8B424" stopOpacity="0" />
                    <stop offset=".5" stopColor="#FCCB4D" stopOpacity=".95" />
                    <stop offset="1" stopColor="#F8B424" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M20 52 Q380 -18 740 52" fill="none" stroke="url(#bridge)" strokeWidth="1.8" pathLength={1} strokeDasharray="1" strokeDashoffset="1" className={cn(assembled && 'animate-draw')} />
                {[0.12, 0.26, 0.4, 0.5, 0.6, 0.74, 0.88].map((p, i) => {
                  const x = 20 + 720 * p
                  const y = 52 - 70 * 4 * p * (1 - p) * 0.5
                  return (
                    <line key={i} x1={x} x2={x} y1={y + 2} y2={52} stroke="#A3AEFB" strokeOpacity=".5" strokeWidth="1"
                      style={{ opacity: assembled ? 1 : 0, transition: `opacity .6s ease ${0.6 + i * 0.08}s` }} />
                  )
                })}
                {assembled && (
                  <circle r="3" fill="#FFF3D6" style={{ filter: 'drop-shadow(0 0 6px #F8B424)' }}>
                    <animateMotion dur="5.5s" repeatCount="indefinite" path="M20 52 Q380 -18 740 52" keyPoints="0;1" keyTimes="0;1" calcMode="linear" />
                  </circle>
                )}
              </svg>
              <div className={cn('mt-2 text-center transition-all duration-1000', assembled ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0')}>
                <p className="font-deva text-2xl font-semibold tracking-wide text-gold-200 [text-shadow:0_0_24px_rgba(248,180,36,.35)] sm:text-[30px]">न्याय सेतु</p>
                {assembled && <div className="tricolor-line mx-auto mt-3 w-40" />}
                <p className="mt-3 text-sm font-medium tracking-wide text-royal-100/85 sm:text-base">
                  One institution · One record · <span className="text-gradient-gold animate-sheen font-semibold">One voice</span>
                </p>
              </div>
            </div>

            <div className="mx-auto mt-9 hidden max-w-[760px] gap-3 sm:grid sm:grid-cols-3">
              {PILLARS.map((p, i) => (
                <div
                  key={p.title}
                  onPointerMove={trackSpotlight}
                  className="glass spotlight group rounded-2xl p-4 transition-[transform,opacity,border-color] duration-700 hover:-translate-y-1 hover:border-gold-300/30"
                  style={{ transitionDelay: assembled ? `${0.15 + i * 0.12}s` : '0s', transform: assembled ? undefined : 'translateY(14px)', opacity: assembled ? 1 : 0 }}
                >
                  <span className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gold-400/10 ring-1 ring-gold-300/25 transition group-hover:bg-gold-400/20">
                    <p.icon className="h-[18px] w-[18px] text-gold-300 transition-transform duration-500 group-hover:scale-110" />
                  </span>
                  <p className="mt-3 text-[13px] font-bold text-white">{p.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-white/60">{p.text}</p>
                </div>
              ))}
            </div>
          </div>

          <footer className="hidden items-center gap-2 text-[11px] text-white/40 lg:flex">
            <ShieldCheck className="h-3.5 w-3.5" />
            Prototype with synthetic demo data · Every match is advisory — officers decide · No complaint data leaves AICTE servers
          </footer>
        </section>

        {/* Form panel */}
        <section className="flex items-center justify-center px-5 pb-10 sm:px-8 lg:py-10">
          <div className="w-full max-w-[440px] animate-rise-in [animation-delay:.35s]">{children}</div>
        </section>
      </div>

      <Link to="/signup" className="absolute right-5 top-5 z-20 hidden text-xs font-semibold text-white/55 transition hover:text-gold-200 lg:block">
        Request access →
      </Link>
    </div>
  )
}
