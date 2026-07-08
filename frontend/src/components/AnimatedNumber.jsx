import { useEffect, useRef, useState } from 'react'
import { animate } from 'framer-motion'

/**
 * Counts up to `value` on mount / whenever it changes.
 * Falls back to the raw value for non-numeric input (e.g. '—').
 */
export default function AnimatedNumber({ value, duration = 1.1, className, style }) {
  const numeric = typeof value === 'number' && Number.isFinite(value)
  const [display, setDisplay] = useState(numeric ? 0 : value)
  const prev = useRef(0)

  useEffect(() => {
    if (!numeric) { setDisplay(value); return }
    const controls = animate(prev.current, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    prev.current = value
    return () => controls.stop()
  }, [value, numeric, duration])

  return (
    <span className={className} style={style}>
      {numeric ? display.toLocaleString() : display}
    </span>
  )
}
