const CFG = {
  critical: { label: 'CRITICAL', cls: 'neon-red',    bg: 'rgba(255,32,32,0.1)',    border: '#FF2020' },
  high:     { label: 'HIGH',     cls: 'neon-orange',  bg: 'rgba(255,85,34,0.1)',    border: '#FF5522' },
  medium:   { label: 'MEDIUM',   cls: 'neon-yellow',  bg: 'rgba(245,200,66,0.1)',   border: '#F5C842' },
  low:      { label: 'LOW',      cls: 'neon-cyan',    bg: 'rgba(255,170,51,0.1)',   border: '#FFAA33' },
  info:     { label: 'INFO',     cls: 'text-fg-muted',bg: 'rgba(88,68,68,0.1)',     border: '#584444' },
}

export default function SeverityBadge({ severity }) {
  const { label, cls, bg, border } = CFG[severity] ?? CFG.info
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[11px] font-display font-bold tracking-widest leading-none ${cls}`}
      style={{
        background: bg,
        border: `1px solid ${border}50`,
        clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
      }}
    >
      {label}
    </span>
  )
}
