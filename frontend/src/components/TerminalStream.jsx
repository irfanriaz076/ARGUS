import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal, Wifi, WifiOff, Trash2 } from 'lucide-react'
import { useEngagementStream } from '../hooks/useWebSocket'

const PLUGIN_COLORS = {
  nmap_scanner:   '#CC0000',
  subfinder:      '#FFAA33',
  httpx_probe:    '#F04343',
  nuclei_scanner: '#FF2020',
  ffuf_fuzzer:    '#F5C842',
}

function lineColor(log) {
  if (log.type === 'complete') return '#CC0000'
  if (log.type === 'error')    return '#FF2020'
  if (log.plugin)              return PLUGIN_COLORS[log.plugin] ?? '#FFAA33'
  if (log.data?.startsWith('[ARGUS]')) return '#FFAA33'
  return '#886868'
}

export default function TerminalStream({ engagementId }) {
  const { logs, connected, clear } = useEngagementStream(engagementId)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  return (
    <div className="hud-card flex flex-col" style={{ height: 400 }}>
      <span className="corner-tl" /><span className="corner-tr" />
      <span className="corner-bl" /><span className="corner-br" />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 pb-2.5 border-b border-border">
        <div className="flex items-center gap-2">
          <Terminal size={13} className="neon-green" />
          <span className="font-display text-[11px] tracking-widest neon-green">LIVE OUTPUT</span>
          <span className="text-[11px] font-mono text-fg-dim">{logs.length} lines</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[12px] font-mono">
            {connected ? (
              <>
                <Wifi size={11} className="neon-green" />
                <span className="neon-green">LIVE</span>
              </>
            ) : (
              <>
                <WifiOff size={11} className="text-fg-dim" />
                <span className="text-fg-dim">IDLE</span>
              </>
            )}
          </div>
          <button
            onClick={clear}
            className="text-fg-dim hover:neon-red transition-colors p-1"
            aria-label="Clear terminal"
          >
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {/* Terminal body */}
      <div
        className="flex-1 overflow-y-auto font-mono text-[12px] leading-relaxed p-2"
        style={{
          background: 'rgba(0,0,0,0.55)',
          border: '1px solid rgba(34,34,58,0.8)',
        }}
      >
        {logs.length === 0 && (
          <div className="flex items-center gap-2 text-fg-dim py-2">
            <span className="neon-green">{'>'}</span>
            <span>{connected ? 'Awaiting scan output...' : 'Start engagement to stream output.'}</span>
            <span className="w-1.5 h-4 bg-neon-green inline-block ml-0.5 animate-neon-pulse" />
          </div>
        )}

        <AnimatePresence initial={false}>
          {logs.map((log, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.12 }}
              className="flex items-start gap-2 hover:bg-white/[0.02] px-1 py-0.5 rounded-sm"
              style={{ color: lineColor(log) }}
            >
              <span className="select-none text-[10px] text-fg-dim w-7 text-right flex-shrink-0 mt-0.5 tabular-nums">
                {i + 1}
              </span>
              {log.plugin && (
                <span
                  className="text-[10px] px-1.5 flex-shrink-0"
                  style={{
                    background: `${PLUGIN_COLORS[log.plugin] ?? '#00CAFF'}14`,
                    border: `1px solid ${PLUGIN_COLORS[log.plugin] ?? '#00CAFF'}35`,
                    color: PLUGIN_COLORS[log.plugin] ?? '#00CAFF',
                    borderRadius: '2px',
                    lineHeight: '1.6',
                  }}
                >
                  {log.plugin.replace('_scanner', '').replace('_probe', '').toUpperCase()}
                </span>
              )}
              <span className="break-all leading-relaxed">{log.data}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
