import { useEffect, useRef } from 'react'

const COLORS = ['#CC0000', '#FFAA33', '#F04343']
const COUNT  = 28
const RANGE  = 110

export default function ParticleField() {
  const canvasRef = useRef(null)
  const rafRef    = useRef(null)
  const mouseRef  = useRef({ x: -9999, y: -9999 })

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')

    const resize = () => {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const onMouse = (e) => { mouseRef.current = { x: e.clientX, y: e.clientY } }
    window.addEventListener('mousemove', onMouse)

    const particles = Array.from({ length: COUNT }, () => ({
      x:  Math.random() * canvas.width,
      y:  Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      r:  Math.random() * 1.2 + 0.3,
      c:  COLORS[Math.floor(Math.random() * COLORS.length)],
      o:  Math.random() * 0.35 + 0.15,
    }))

    const tick = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const { x: mx, y: my } = mouseRef.current

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]

        const dx = mx - p.x, dy = my - p.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 90) {
          p.vx -= (dx / dist) * 0.03
          p.vy -= (dy / dist) * 0.03
        }

        p.vx = Math.max(-0.5, Math.min(0.5, p.vx))
        p.vy = Math.max(-0.5, Math.min(0.5, p.vy))
        p.x += p.vx
        p.y += p.vy

        if (p.x < 0)            p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0)            p.y = canvas.height
        if (p.y > canvas.height)p.y = 0

        for (let j = i + 1; j < particles.length; j++) {
          const q  = particles[j]
          const ex = p.x - q.x, ey = p.y - q.y
          const ed = Math.sqrt(ex * ex + ey * ey)
          if (ed < RANGE) {
            ctx.save()
            ctx.globalAlpha = (1 - ed / RANGE) * 0.14
            ctx.strokeStyle = p.c
            ctx.lineWidth   = 0.5
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(q.x, q.y)
            ctx.stroke()
            ctx.restore()
          }
        }

        ctx.save()
        ctx.globalAlpha = p.o
        ctx.fillStyle   = p.c
        ctx.shadowBlur  = 6
        ctx.shadowColor = p.c
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
      }

      rafRef.current = requestAnimationFrame(tick)
    }
    tick()

    return () => {
      cancelAnimationFrame(rafRef.current)
      window.removeEventListener('resize', resize)
      window.removeEventListener('mousemove', onMouse)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.28,
      }}
    />
  )
}
