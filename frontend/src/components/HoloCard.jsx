import { useRef } from 'react'
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'

export default function HoloCard({
  children,
  className = '',
  glowColor = 'rgba(204,0,0,0.2)',
  shimmerColor = 'rgba(240,67,67,0.12)',
  intensity = 1,
  corners = false,
}) {
  const ref  = useRef(null)
  const rawX = useMotionValue(0)
  const rawY = useMotionValue(0)
  const x    = useSpring(rawX, { stiffness: 200, damping: 28 })
  const y    = useSpring(rawY, { stiffness: 200, damping: 28 })

  const rotateX   = useTransform(y, [-0.5, 0.5], [5.5 * intensity, -5.5 * intensity])
  const rotateY   = useTransform(x, [-0.5, 0.5], [-5.5 * intensity, 5.5 * intensity])
  const shimmerPX = useTransform(x, [-0.5, 0.5], [15, 85])
  const shimmerPY = useTransform(y, [-0.5, 0.5], [15, 85])
  const shimmerBg = useTransform(
    [shimmerPX, shimmerPY],
    ([sx, sy]) =>
      `radial-gradient(circle at ${sx}% ${sy}%, ${shimmerColor} 0%, rgba(255,170,51,0.045) 50%, transparent 70%)`
  )
  const edgeGlow = useTransform(
    [x, y],
    ([lx, ly]) => {
      const m = Math.sqrt(lx * lx + ly * ly) * 2
      return `0 0 ${12 * m}px ${glowColor}`
    }
  )

  const onMouseMove = (e) => {
    const r = ref.current.getBoundingClientRect()
    rawX.set((e.clientX - r.left) / r.width  - 0.5)
    rawY.set((e.clientY - r.top)  / r.height - 0.5)
  }
  const onMouseLeave = () => { rawX.set(0); rawY.set(0) }

  return (
    <motion.div
      ref={ref}
      className={`relative ${className}`}
      style={{ rotateX, rotateY, transformPerspective: 1100, transformStyle: 'preserve-3d' }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      whileHover={{ scale: 1.008 }}
      transition={{ scale: { duration: 0.22, ease: 'easeOut' } }}
    >
      <motion.div
        className="absolute inset-0 pointer-events-none"
        style={{ boxShadow: edgeGlow }}
      />
      <motion.div
        className="absolute inset-0 pointer-events-none z-10"
        style={{ background: shimmerBg }}
      />
      {corners && (
        <>
          <span className="corner-tl" />
          <span className="corner-tr" />
          <span className="corner-bl" />
          <span className="corner-br" />
        </>
      )}
      <div style={{ transform: 'translateZ(8px)' }}>
        {children}
      </div>
    </motion.div>
  )
}
