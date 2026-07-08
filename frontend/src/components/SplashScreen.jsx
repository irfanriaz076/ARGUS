import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const BOOT_LINES = [
  'INITIALIZING CORE SYSTEMS...',
  'LOADING PLUGIN REGISTRY...',
  'CONNECTING TO THREAT DATABASE...',
  'CALIBRATING KILL CHAIN ENGINE...',
  'ALL SYSTEMS ONLINE',
]

export default function SplashScreen({ onDone }) {
  const [progress, setProgress]   = useState(0)
  const [lines, setLines]         = useState([])
  const [exiting, setExiting]     = useState(false)

  useEffect(() => {
    // Progress bar
    const progTimer = setInterval(() => {
      setProgress(p => {
        if (p >= 100) { clearInterval(progTimer); return 100 }
        return p + 2
      })
    }, 30)

    // Boot lines appear one by one
    BOOT_LINES.forEach((line, i) => {
      setTimeout(() => setLines(l => [...l, line]), 400 + i * 320)
    })

    // Start exit after boot sequence
    const exitTimer = setTimeout(() => setExiting(true), 2600)
    const doneTimer = setTimeout(() => onDone(), 3100)

    return () => {
      clearInterval(progTimer)
      clearTimeout(exitTimer)
      clearTimeout(doneTimer)
    }
  }, [onDone])

  return (
    <AnimatePresence>
      {!exiting && (
        <motion.div
          key="splash"
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center"
          style={{ background: '#000000' }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.5, ease: 'easeInOut' }}
        >
          {/* Scanline overlay */}
          <div className="absolute inset-0 pointer-events-none"
            style={{
              backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.08) 2px, rgba(0,0,0,0.08) 4px)',
            }}
          />

          {/* Corner brackets */}
          {[
            'top-6 left-6 border-t border-l',
            'top-6 right-6 border-t border-r',
            'bottom-6 left-6 border-b border-l',
            'bottom-6 right-6 border-b border-r',
          ].map((cls, i) => (
            <motion.div
              key={i}
              className={`absolute w-10 h-10 ${cls}`}
              style={{ borderColor: 'rgba(204,0,0,0.4)' }}
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.4 }}
            />
          ))}

          <div className="flex flex-col items-center gap-8 px-8 max-w-md w-full">

            {/* Logo */}
            <motion.div
              className="flex flex-col items-center gap-4"
              initial={{ opacity: 0, scale: 0.6, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <motion.img
                src="/argus-logo.png"
                alt="ARGUS"
                draggable={false}
                className="w-[340px] max-w-full h-auto"
                style={{ userSelect: 'none' }}
                animate={{
                  filter: [
                    'drop-shadow(0 10px 22px rgba(0,0,0,0.75)) drop-shadow(0 0 2px rgba(204,0,0,0.3))',
                    'drop-shadow(0 10px 22px rgba(0,0,0,0.75)) drop-shadow(0 0 7px rgba(204,0,0,0.5))',
                    'drop-shadow(0 10px 22px rgba(0,0,0,0.75)) drop-shadow(0 0 2px rgba(204,0,0,0.3))',
                  ],
                }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              />

              <motion.div className="text-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, duration: 0.5 }}>
                <div className="text-[11px] font-mono tracking-widest text-fg-dim">
                  AUTONOMOUS RECONNAISSANCE &amp; GUIDED UNIFIED SCANNER
                </div>
              </motion.div>
            </motion.div>

            {/* Progress bar */}
            <motion.div
              className="w-full space-y-2"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
            >
              <div className="w-full h-px bg-border rounded overflow-hidden">
                <motion.div
                  className="h-full"
                  style={{
                    background: 'linear-gradient(90deg, #CC0000, #FF4433)',
                    boxShadow: '0 0 8px rgba(204,0,0,0.7)',
                  }}
                  initial={{ scaleX: 0, originX: 0 }}
                  animate={{ scaleX: progress / 100 }}
                  transition={{ ease: 'linear' }}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-fg-dim">
                <span>LOADING</span>
                <span style={{ color: '#CC0000' }}>{progress}%</span>
              </div>
            </motion.div>

            {/* Boot log */}
            <div className="w-full space-y-1.5 min-h-[120px]">
              <AnimatePresence>
                {lines.map((line, i) => (
                  <motion.div
                    key={line}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                    className="flex items-center gap-2 font-mono text-[11px]"
                  >
                    <span style={{ color: '#CC0000' }}>{'>'}</span>
                    <span className={i === lines.length - 1 && line === 'ALL SYSTEMS ONLINE'
                      ? 'neon-green'
                      : 'text-fg-muted'}>
                      {line}
                    </span>
                    {i === lines.length - 1 && (
                      <motion.span
                        className="inline-block w-1.5 h-3"
                        style={{ background: '#CC0000' }}
                        animate={{ opacity: [1, 0, 1] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                      />
                    )}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {/* Version */}
            <motion.div
              className="text-[9px] font-mono text-fg-dim tracking-widest"
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              transition={{ delay: 1 }}
            >
              v2.0 · ARGUS SECURITY PLATFORM · CLASSIFIED
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
