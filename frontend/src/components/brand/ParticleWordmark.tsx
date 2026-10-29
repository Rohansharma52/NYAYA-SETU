import { useEffect, useRef } from 'react'

interface ParticleWordmarkProps {
  text?: string
  className?: string
  /** Called once the particles have converged into the wordmark */
  onAssembled?: () => void
  fontFamily?: string
  interactive?: boolean
}

// Gold → ivory → gold gradient sampled across the width of the wordmark
const PALETTE = ['#F5B730', '#F8C24A', '#FBD46F', '#FDE6A4', '#FFF3D6', '#FDE6A4', '#FBD46F', '#F8C24A', '#F5B730', '#EFA51A']

function hexToRgb(hex: string) {
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

/**
 * Canvas particle field that assembles itself into the NYAYA SETU wordmark.
 * Particles drift in from a scattered dust cloud, sweep left → right into the
 * letterforms with spring physics, then glow, shimmer and react to the cursor.
 */
export function ParticleWordmark({
  text = 'NYAYA SETU',
  className,
  onAssembled,
  fontFamily = 'Cinzel',
  interactive = true,
}: ParticleWordmarkProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const assembledRef = useRef(onAssembled)
  assembledRef.current = onAssembled

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    let W = 0
    let H = 0
    let dpr = 1
    let raf = 0
    let disposed = false
    let start = 0
    let firedAssembled = false
    let glow: HTMLCanvasElement | null = null

    // Particle state (struct-of-arrays for speed)
    let N = 0
    let px = new Float32Array(0)
    let py = new Float32Array(0)
    let vx = new Float32Array(0)
    let vy = new Float32Array(0)
    let tx = new Float32Array(0)
    let ty = new Float32Array(0)
    let delay = new Float32Array(0)
    let size = new Float32Array(0)
    let tone = new Uint8Array(0)
    let phase = new Float32Array(0)

    // Ambient dust
    const AMB = 140
    const ax = new Float32Array(AMB)
    const ay = new Float32Array(AMB)
    const as = new Float32Array(AMB)
    const asp = new Float32Array(AMB)
    const aph = new Float32Array(AMB)

    const mouse = { x: -9999, y: -9999, active: false }
    const rgb = PALETTE.map(hexToRgb)

    function layoutText(target: CanvasRenderingContext2D, w: number, h: number) {
      const chars = text.split('')
      let fontSize = Math.min(h * 0.62, 150)
      const spacingRatio = 0.12
      const measure = (fs: number) => {
        target.font = `700 ${fs}px ${fontFamily}, "Times New Roman", serif`
        const widths = chars.map((c) => target.measureText(c).width)
        const total = widths.reduce((a, b) => a + b, 0) + fs * spacingRatio * (chars.length - 1)
        return { widths, total }
      }
      let m = measure(fontSize)
      while (m.total > w * 0.94 && fontSize > 18) {
        fontSize -= 2
        m = measure(fontSize)
      }
      target.textBaseline = 'middle'
      let x = (w - m.total) / 2
      const y = h / 2
      chars.forEach((c, i) => {
        target.fillText(c, x, y)
        x += m.widths[i] + fontSize * spacingRatio
      })
      return fontSize
    }

    function buildTargets() {
      const off = document.createElement('canvas')
      off.width = Math.max(1, Math.floor(W))
      off.height = Math.max(1, Math.floor(H))
      const o = off.getContext('2d', { willReadFrequently: true })
      if (!o) return
      o.fillStyle = '#fff'
      const fontSize = layoutText(o, off.width, off.height)
      const img = o.getImageData(0, 0, off.width, off.height).data
      let gap = fontSize > 60 ? 3 : 2
      let pts: number[] = []
      const sample = (g: number) => {
        pts = []
        for (let y = 0; y < off.height; y += g) {
          for (let x = 0; x < off.width; x += g) {
            if (img[(y * off.width + x) * 4 + 3] > 130) pts.push(x, y)
          }
        }
      }
      sample(gap)
      while (pts.length / 2 > 6500 && gap < 8) {
        gap += 1
        sample(gap)
      }

      // Pre-render glow layer used once the text is assembled
      glow = document.createElement('canvas')
      glow.width = Math.floor(W * dpr)
      glow.height = Math.floor(H * dpr)
      const g = glow.getContext('2d')
      if (g) {
        g.scale(dpr, dpr)
        g.filter = 'blur(14px)'
        g.fillStyle = 'rgba(248,180,36,0.55)'
        layoutText(g, W, H)
        g.filter = 'blur(3px)'
        g.fillStyle = 'rgba(255,236,190,0.35)'
        layoutText(g, W, H)
      }

      const count = pts.length / 2
      const prev = { N, px, py, vx, vy }
      N = count
      px = new Float32Array(N)
      py = new Float32Array(N)
      vx = new Float32Array(N)
      vy = new Float32Array(N)
      tx = new Float32Array(N)
      ty = new Float32Array(N)
      delay = new Float32Array(N)
      size = new Float32Array(N)
      tone = new Uint8Array(N)
      phase = new Float32Array(N)
      const cx = W / 2
      const cy = H / 2
      for (let i = 0; i < N; i++) {
        tx[i] = pts[i * 2]
        ty[i] = pts[i * 2 + 1]
        if (prev.N > 0) {
          // On resize, re-flow from the current positions
          const j = i % prev.N
          px[i] = prev.px[j]
          py[i] = prev.py[j]
          delay[i] = 0
        } else {
          // Scattered dust cloud, biased away from the centre
          const ang = Math.random() * Math.PI * 2
          const rad = (0.35 + Math.random() * 0.9) * Math.max(W, H) * 0.65
          px[i] = cx + Math.cos(ang) * rad
          py[i] = cy + Math.sin(ang) * rad * 0.55
          // Left → right sweep with jitter
          delay[i] = (tx[i] / W) * 900 + Math.random() * 650
        }
        vx[i] = (Math.random() - 0.5) * 0.6
        vy[i] = (Math.random() - 0.5) * 0.6
        size[i] = gap * (0.62 + Math.random() * 0.38)
        tone[i] = Math.min(PALETTE.length - 1, Math.floor((tx[i] / W) * PALETTE.length))
        phase[i] = Math.random() * Math.PI * 2
      }
    }

    function initAmbient() {
      for (let i = 0; i < AMB; i++) {
        ax[i] = Math.random() * W
        ay[i] = Math.random() * H
        as[i] = Math.random() * 1.4 + 0.3
        asp[i] = Math.random() * 0.25 + 0.05
        aph[i] = Math.random() * Math.PI * 2
      }
    }

    function resize() {
      const rect = canvas!.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      W = rect.width
      H = rect.height
      canvas!.width = Math.floor(W * dpr)
      canvas!.height = Math.floor(H * dpr)
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      buildTargets()
      if (!ax[0] && !ay[0]) initAmbient()
    }

    function frame(now: number) {
      if (disposed) return
      if (!start) start = now
      const t = now - start
      ctx!.clearRect(0, 0, W, H)

      // Ambient dust (drifts upward, twinkles)
      ctx!.globalCompositeOperation = 'lighter'
      for (let i = 0; i < AMB; i++) {
        ay[i] -= asp[i]
        if (ay[i] < -4) {
          ay[i] = H + 4
          ax[i] = Math.random() * W
        }
        const a = 0.25 + 0.35 * Math.sin(t * 0.0015 + aph[i])
        ctx!.fillStyle = `rgba(199,207,254,${Math.max(0.05, a)})`
        ctx!.fillRect(ax[i], ay[i], as[i], as[i])
      }

      // Glow behind assembled text
      const settle = Math.min(1, Math.max(0, (t - 2100) / 900))
      if (glow && settle > 0) {
        ctx!.globalAlpha = settle * (0.75 + 0.25 * Math.sin(t * 0.0012))
        ctx!.drawImage(glow, 0, 0, W, H)
        ctx!.globalAlpha = 1
      }

      // Shine band sweeping across every ~6s once assembled
      const shineX = settle > 0 ? ((t - 2400) % 6000) / 6000 * (W + 400) - 200 : -9999
      const springK = 0.018 + Math.min(0.03, t / 120000)
      let moving = 0
      for (let i = 0; i < N; i++) {
        if (t < delay[i]) {
          px[i] += vx[i]
          py[i] += vy[i]
        } else {
          let fx = (tx[i] - px[i]) * springK
          let fy = (ty[i] - py[i]) * springK
          if (interactive && mouse.active) {
            const dx = px[i] - mouse.x
            const dy = py[i] - mouse.y
            const d2 = dx * dx + dy * dy
            if (d2 < 4900) {
              const f = (1 - d2 / 4900) * 2.4
              const d = Math.sqrt(d2) || 1
              fx += (dx / d) * f
              fy += (dy / d) * f
            }
          }
          vx[i] = (vx[i] + fx) * 0.86
          vy[i] = (vy[i] + fy) * 0.86
          px[i] += vx[i]
          py[i] += vy[i]
          if (settle > 0) {
            // breathing micro-motion
            px[i] += Math.sin(t * 0.002 + phase[i]) * 0.05
          }
        }
        if (Math.abs(vx[i]) + Math.abs(vy[i]) > 0.15) moving++
      }

      // Draw particles grouped by colour to minimise state changes
      for (let c = 0; c < PALETTE.length; c++) {
        const [r, g, b] = rgb[c]
        ctx!.fillStyle = `rgb(${r},${g},${b})`
        for (let i = 0; i < N; i++) {
          if (tone[i] !== c) continue
          const s = size[i]
          let alpha = t < delay[i] ? 0.45 : 0.95
          if (settle > 0) alpha = 0.82 + 0.18 * Math.sin(t * 0.003 + phase[i])
          const shine = Math.abs(px[i] - shineX) < 70 ? 1 - Math.abs(px[i] - shineX) / 70 : 0
          ctx!.globalAlpha = Math.min(1, alpha + shine * 0.6)
          ctx!.fillRect(px[i] - s / 2, py[i] - s / 2, s, s)
        }
      }
      // White sparkle on the shine band
      if (shineX > -500) {
        ctx!.fillStyle = '#fff'
        for (let i = 0; i < N; i += 3) {
          const dd = Math.abs(px[i] - shineX)
          if (dd < 22) {
            ctx!.globalAlpha = (1 - dd / 22) * 0.9
            ctx!.fillRect(px[i] - 0.8, py[i] - 0.8, 1.6, 1.6)
          }
        }
      }
      ctx!.globalAlpha = 1
      ctx!.globalCompositeOperation = 'source-over'

      if (!firedAssembled && t > 1500 && moving < N * 0.04) {
        firedAssembled = true
        assembledRef.current?.()
      }
      raf = requestAnimationFrame(frame)
    }

    function drawStatic() {
      ctx!.clearRect(0, 0, W, H)
      if (glow) ctx!.drawImage(glow, 0, 0, W, H)
      ctx!.fillStyle = '#F8C24A'
      for (let i = 0; i < N; i++) ctx!.fillRect(tx[i] - size[i] / 2, ty[i] - size[i] / 2, size[i], size[i])
      assembledRef.current?.()
    }

    const onMove = (e: PointerEvent) => {
      const r = canvas!.getBoundingClientRect()
      mouse.x = e.clientX - r.left
      mouse.y = e.clientY - r.top
      mouse.active = true
    }
    const onLeave = () => {
      mouse.active = false
      mouse.x = mouse.y = -9999
    }
    let resizeTimer = 0
    const onResize = () => {
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(() => {
        resize()
        if (reduceMotion) drawStatic()
      }, 120)
    }
    const onVisibility = () => {
      if (document.hidden) cancelAnimationFrame(raf)
      else if (!reduceMotion) raf = requestAnimationFrame(frame)
    }

    const fontReady = (document as Document & { fonts?: FontFaceSet }).fonts
      ? Promise.race([
          document.fonts.load(`700 100px ${fontFamily}`).catch(() => undefined),
          new Promise((r) => setTimeout(r, 1600)),
        ])
      : Promise.resolve()

    fontReady.then(() => {
      if (disposed) return
      resize()
      if (reduceMotion) {
        drawStatic()
        return
      }
      raf = requestAnimationFrame(frame)
      window.addEventListener('resize', onResize)
      document.addEventListener('visibilitychange', onVisibility)
      if (interactive) {
        window.addEventListener('pointermove', onMove, { passive: true })
        canvas.addEventListener('pointerleave', onLeave)
      }
    })

    return () => {
      disposed = true
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pointermove', onMove)
      canvas.removeEventListener('pointerleave', onLeave)
    }
  }, [text, fontFamily, interactive])

  return <canvas ref={canvasRef} className={className} aria-label={text} role="img" />
}
