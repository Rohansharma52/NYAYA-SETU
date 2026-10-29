import { useEffect, useRef } from 'react'

/**
 * Slow-drifting network of nodes joined by faint links: complaints (nodes) being
 * connected across bureaus. Nodes lean toward the cursor; links near the cursor
 * brighten. Pauses when the tab is hidden; static frame under reduced motion.
 */
export function ConstellationField({ className, density = 1 }: { className?: string; density?: number }) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

    let W = 0, H = 0, dpr = 1, raf = 0, running = true
    type P = { x: number; y: number; vx: number; vy: number; r: number; hue: number; tw: number }
    let pts: P[] = []
    const mouse = { x: -1e4, y: -1e4 }
    // saffron, ivory, royal, green — a restrained tricolour-plus-brand set
    const HUES = ['248,180,36', '255,240,214', '124,136,245', '74,222,128']

    function resize() {
      const rect = canvas!.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      W = rect.width; H = rect.height
      canvas!.width = W * dpr; canvas!.height = H * dpr
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      const n = Math.round(Math.min(110, (W * H) / 15000) * density)
      pts = Array.from({ length: n }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.18, vy: (Math.random() - 0.5) * 0.18,
        r: Math.random() * 1.4 + 0.6,
        hue: Math.random() < 0.55 ? 2 : Math.random() < 0.6 ? 0 : Math.random() < 0.5 ? 1 : 3,
        tw: Math.random() * Math.PI * 2,
      }))
    }

    function frame(t: number) {
      ctx!.clearRect(0, 0, W, H)
      const LINK = Math.min(150, Math.max(90, W / 11))
      for (const p of pts) {
        if (!reduce) {
          const dx = mouse.x - p.x, dy = mouse.y - p.y, d2 = dx * dx + dy * dy
          if (d2 < 220 * 220) { p.vx += dx * 0.000012; p.vy += dy * 0.000012 }
          p.vx *= 0.995; p.vy *= 0.995
          p.vx += (Math.random() - 0.5) * 0.004; p.vy += (Math.random() - 0.5) * 0.004
          p.x += p.vx; p.y += p.vy
          if (p.x < -20) p.x = W + 20; if (p.x > W + 20) p.x = -20
          if (p.y < -20) p.y = H + 20; if (p.y > H + 20) p.y = -20
        }
      }
      ctx!.lineWidth = 0.7
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i]
        for (let j = i + 1; j < pts.length; j++) {
          const b = pts[j]
          const dx = a.x - b.x, dy = a.y - b.y, d = Math.hypot(dx, dy)
          if (d < LINK) {
            const mx = (a.x + b.x) / 2 - mouse.x, my = (a.y + b.y) / 2 - mouse.y
            const near = Math.max(0, 1 - Math.hypot(mx, my) / 240)
            const alpha = (1 - d / LINK) * (0.13 + near * 0.45)
            ctx!.strokeStyle = near > 0.15 ? `rgba(248,196,74,${alpha})` : `rgba(140,152,245,${alpha})`
            ctx!.beginPath(); ctx!.moveTo(a.x, a.y); ctx!.lineTo(b.x, b.y); ctx!.stroke()
          }
        }
      }
      for (const p of pts) {
        const tw = reduce ? 0.8 : 0.55 + 0.45 * Math.sin(t / 900 + p.tw)
        ctx!.fillStyle = `rgba(${HUES[p.hue]},${0.35 + tw * 0.5})`
        ctx!.beginPath(); ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx!.fill()
      }
      if (!reduce && running) raf = requestAnimationFrame(frame)
    }

    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect()
      mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top
    }
    const onLeave = () => { mouse.x = -1e4; mouse.y = -1e4 }
    const onVis = () => {
      running = !document.hidden
      cancelAnimationFrame(raf)
      if (running && !reduce) raf = requestAnimationFrame(frame)
    }

    resize()
    raf = requestAnimationFrame(frame)
    const ro = new ResizeObserver(() => { resize(); if (reduce) frame(0) })
    ro.observe(canvas)
    window.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerleave', onLeave)
    document.addEventListener('visibilitychange', onVis)
    return () => {
      cancelAnimationFrame(raf); ro.disconnect()
      window.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerleave', onLeave)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [density])

  return <canvas ref={ref} className={className} aria-hidden />
}
