import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Crosshair, ArrowRight } from 'lucide-react'
import { graphApi } from '../api/client'

const SEV_COLOR = {
  critical: '#FF2020', high: '#F04343', medium: '#F5C842', low: '#FFAA33',
}

/**
 * One-line "most exploitable route" banner for the Overview tab.
 * Renders nothing until a path is found; clicking jumps to the Graph tab.
 */
export default function TopAttackPath({ engagementId, onViewGraph }) {
  const [path, setPath] = useState(null)

  useEffect(() => {
    let alive = true
    graphApi.attackPaths(engagementId)
      .then(d => { if (alive) setPath((d.paths || [])[0] || null) })
      .catch(() => { /* graph may not be ready yet */ })
    return () => { alive = false }
  }, [engagementId])

  if (!path) return null
  const col = SEV_COLOR[path.severity] || '#FFAA33'

  return (
    <motion.button
      onClick={onViewGraph}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full text-left hud-card group"
      style={{ borderColor: `${col}40` }}
    >
      <div className="flex items-center gap-3">
        <motion.div
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2.2, repeat: Infinity }}
          className="flex-shrink-0"
        >
          <Crosshair size={16} style={{ color: col }} />
        </motion.div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="section-label" style={{ color: col, marginBottom: 0 }}>
              Most Exploitable Route
            </span>
            <span
              className="text-[9px] font-display font-black tracking-wider px-1.5 py-0.5"
              style={{
                color: col, border: `1px solid ${col}55`, background: `${col}12`,
                clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
              }}
            >
              SCORE {path.score}
            </span>
            <span className="text-[9px] font-mono text-fg-muted">
              → {path.target.reason}
            </span>
          </div>
          <p className="text-[12px] font-mono text-fg mt-1 truncate">
            {path.rationale}
          </p>
        </div>

        <span className="text-[10px] font-mono text-fg-dim flex items-center gap-1 flex-shrink-0 group-hover:neon-cyan transition-colors">
          TRACE <ArrowRight size={11} />
        </span>
      </div>
    </motion.button>
  )
}
