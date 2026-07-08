import { motion } from 'framer-motion'

const HEIGHT = { xs: 22, sm: 30, md: 40, lg: 60, xl: 96, '2xl': 132 }
const TEXT   = { xs: 'text-xs', sm: 'text-sm', md: 'text-lg', lg: 'text-2xl', xl: 'text-4xl', '2xl': 'text-6xl' }

// Soft dark drop-shadow gives the mark a floating, 3D lift against the background —
// no wide red "splash", so the logo merges cleanly with black.
const LIFT = 'drop-shadow(0 8px 18px rgba(0,0,0,0.7))'

/**
 * ARGUS brand mark — renders the official logo asset.
 *   variant="icon"    → the eye/reticle mark only    (/argus-icon.png)
 *   variant="full"    → full banner: mark + wordmark  (/argus-logo.png)
 *   variant="lockup"  → eye mark + Orbitron wordmark    (default, compact)
 */
export default function ArgusLogo({ size = 'md', variant = 'lockup', animated = false, className = '' }) {
  const h = HEIGHT[size] ?? 40
  const base = { height: h, width: 'auto', userSelect: 'none' }

  // Animated: faint red pulse layered on the dark lift. Static: just the lift.
  const motionProps = animated
    ? {
        style: base,
        animate: {
          filter: [
            `${LIFT} drop-shadow(0 0 2px rgba(204,0,0,0.30))`,
            `${LIFT} drop-shadow(0 0 6px rgba(204,0,0,0.5))`,
            `${LIFT} drop-shadow(0 0 2px rgba(204,0,0,0.30))`,
          ],
        },
        transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
      }
    : { style: { ...base, filter: LIFT } }

  if (variant === 'full') {
    return (
      <motion.img
        src="/argus-logo.png"
        alt="ARGUS — Automated Red Team Operations"
        draggable={false}
        className={className}
        {...motionProps}
      />
    )
  }

  if (variant === 'icon') {
    return (
      <motion.img
        src="/argus-icon.png"
        alt="ARGUS"
        draggable={false}
        className={className}
        {...motionProps}
      />
    )
  }

  // lockup — eye mark + Orbitron wordmark
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <motion.img
        src="/argus-icon.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        {...motionProps}
      />
      <span className={`font-display font-black tracking-[0.22em] neon-green ${TEXT[size] ?? 'text-lg'}`}>
        ARGUS
      </span>
    </div>
  )
}
