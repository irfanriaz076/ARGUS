import { motion } from 'framer-motion'
import { Check, Loader } from 'lucide-react'

const STAGES = [
  { id: 'recon',             label: 'RECON' },
  { id: 'enumeration',       label: 'ENUM' },
  { id: 'vulnerability',     label: 'VULN' },
  { id: 'exploitation',      label: 'EXPLOIT' },
  { id: 'post_exploitation', label: 'POST-EX' },
]

function stageStatus(scans, id, engStatus) {
  if (engStatus === 'complete') return 'done'
  const s = scans.filter(sc => sc.stage === id)
  if (!s.length) return 'idle'
  if (s.every(sc => sc.status === 'complete')) return 'done'
  if (s.some(sc => sc.status === 'running' || sc.status === 'queued')) return 'active'
  return 'idle'
}

export default function StageProgress({ scans = [], engagementStatus }) {
  return (
    <div className="flex items-center gap-0">
      {STAGES.map((stage, i) => {
        const status   = stageStatus(scans, stage.id, engagementStatus)
        const isDone   = status === 'done'
        const isActive = status === 'active'
        const color    = isDone ? '#CC0000' : isActive ? '#FFAA33' : '#261414'
        const textCls  = isDone ? 'neon-green' : isActive ? 'neon-cyan animate-neon-pulse' : 'text-fg-dim'

        return (
          <div key={stage.id} className="flex items-center">
            <div className="flex flex-col items-center gap-2">
              <motion.div
                className="w-8 h-8 rounded-sm flex items-center justify-center"
                style={{
                  border: `1px solid ${color}`,
                  background: isDone
                    ? 'rgba(204,0,0,0.08)'
                    : isActive
                    ? 'rgba(255,170,51,0.06)'
                    : 'rgba(38,20,20,0.5)',
                  boxShadow: isDone
                    ? '0 0 8px rgba(204,0,0,0.3)'
                    : isActive
                    ? '0 0 8px rgba(255,170,51,0.3)'
                    : 'none',
                }}
                animate={isActive ? {
                  boxShadow: [
                    '0 0 6px rgba(255,170,51,0.3)',
                    '0 0 16px rgba(255,170,51,0.6)',
                    '0 0 6px rgba(255,170,51,0.3)',
                  ]
                } : {}}
                transition={isActive ? { duration: 1.8, repeat: Infinity } : {}}
              >
                {isDone   && <Check  size={13} color="#CC0000" />}
                {isActive && <Loader size={13} color="#FFAA33" className="animate-spin" />}
                {!isDone && !isActive && (
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                )}
              </motion.div>
              <span className={`text-[11px] font-display tracking-widest ${textCls}`}>
                {stage.label}
              </span>
            </div>

            {i < STAGES.length - 1 && (
              <div className="relative h-px w-8 md:w-14 mx-1" style={{ background: '#261414', marginBottom: '20px' }}>
                {isDone && (
                  <motion.div
                    className="absolute inset-0"
                    style={{ background: 'var(--green)', boxShadow: '0 0 4px var(--green)' }}
                    initial={{ scaleX: 0, originX: 0 }}
                    animate={{ scaleX: 1 }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                  />
                )}
                {isActive && <div className="scan-beam" style={{ height: '2px', top: '-1px' }} />}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
