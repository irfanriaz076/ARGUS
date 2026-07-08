import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Grid3x3, ExternalLink } from 'lucide-react'
import HoloCard from './HoloCard'
import { TACTIC_ORDER, TECHNIQUES, techniquesByTactic, attackUrl } from '../lib/mitreCatalog'

const SEV_RANK  = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }
const SEV_COLOR = {
  critical: '#FF2020', high: '#FF5522', medium: '#F5C842', low: '#FFAA33', info: '#886868',
}

function TechniqueCell({ id, meta, hit }) {
  const col = hit ? SEV_COLOR[hit.sev] || '#886868' : null
  return (
    <a
      href={attackUrl(id)}
      target="_blank"
      rel="noopener noreferrer"
      className="block group"
      title={`${id} · ${meta.name}${hit ? ` — ${hit.count} finding(s), max ${hit.sev}` : ' — not observed'}`}
    >
      <div
        className="relative px-2 py-1.5 rounded-sm transition-colors"
        style={{
          background: hit ? `${col}14` : 'transparent',
          border: `1px solid ${hit ? `${col}55` : 'var(--border)'}`,
        }}
      >
        {hit && (
          <span
            className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-sm"
            style={{ background: col, boxShadow: `0 0 5px ${col}` }}
          />
        )}
        <div className="flex items-center gap-1.5">
          <span
            className="text-[10px] font-display font-black tracking-wide"
            style={{ color: hit ? col : 'var(--fg-dim)' }}
          >
            {id}
          </span>
          {hit && (
            <span
              className="ml-auto text-[9px] font-mono px-1 leading-none rounded-sm"
              style={{ color: col, background: `${col}1F` }}
            >
              {hit.count}
            </span>
          )}
        </div>
        <div
          className="text-[9px] font-mono leading-tight mt-0.5 truncate"
          style={{ color: hit ? 'var(--fg-muted)' : 'var(--fg-dim)' }}
        >
          {meta.name}
        </div>
      </div>
    </a>
  )
}

export default function MitreCoverage({ findings }) {
  const coverage = useMemo(() => {
    const map = {}
    for (const f of findings || []) {
      const id = f.evidence?.mitre?.id || f.mitre_technique
      if (!id) continue
      const rank = SEV_RANK[f.severity] ?? 0
      const cur = map[id] || { count: 0, rank: -1, sev: 'info' }
      cur.count += 1
      if (rank > cur.rank) { cur.rank = rank; cur.sev = f.severity }
      map[id] = cur
    }
    return map
  }, [findings])

  const byTactic = useMemo(() => techniquesByTactic(), [])

  const totalTech    = Object.keys(TECHNIQUES).length
  const coveredIds   = Object.keys(coverage).filter(id => TECHNIQUES[id])
  const coveredTech  = coveredIds.length
  const coveredTacs  = new Set(coveredIds.map(id => TECHNIQUES[id].tactic))
  const mappedCount  = Object.values(coverage).reduce((a, c) => a + c.count, 0)
  const pct          = Math.round((coveredTech / totalTech) * 100)

  if (!findings || findings.length === 0) {
    return (
      <HoloCard className="hud-card text-center py-12" corners>
        <Grid3x3 size={26} className="mx-auto text-fg-dim mb-3" />
        <p className="text-fg-muted text-[13px] font-mono">
          No findings yet — run a scan to map coverage across ATT&amp;CK.
        </p>
      </HoloCard>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Summary */}
      <HoloCard className="hud-card" corners glowColor="rgba(240,67,67,0.12)">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="section-label" style={{ color: 'var(--violet)', marginBottom: 0 }}>
            <Grid3x3 size={12} /> ATT&amp;CK Coverage
          </div>
          <div className="flex items-center gap-4 ml-auto text-[11px] font-mono">
            <span className="text-fg-muted">
              Techniques <span className="neon-violet font-display">{coveredTech}</span>
              <span className="text-fg-dim">/{totalTech}</span>
            </span>
            <span className="text-fg-muted">
              Tactics <span className="neon-violet font-display">{coveredTacs.size}</span>
              <span className="text-fg-dim">/{TACTIC_ORDER.length}</span>
            </span>
            <span className="text-fg-muted">
              Mapped <span className="neon-red font-display">{mappedCount}</span>
            </span>
          </div>
        </div>
        <div className="mt-3 h-1 w-full rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg,#F04343,#FF2020)', boxShadow: '0 0 6px rgba(255,32,32,0.6)' }}
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
          />
        </div>
      </HoloCard>

      {/* Matrix — tactic columns */}
      <div className="overflow-x-auto pb-2">
        <div className="flex gap-2.5 min-w-max">
          {TACTIC_ORDER.map(tactic => {
            const ids = byTactic[tactic] || []
            const covered = ids.filter(id => coverage[id]).length
            const active = covered > 0
            return (
              <div key={tactic} className="w-[172px] flex-shrink-0">
                {/* Column header */}
                <div
                  className="px-2 py-2 mb-2 rounded-sm"
                  style={{
                    background: active ? 'rgba(240,67,67,0.06)' : 'var(--card)',
                    border: `1px solid ${active ? 'rgba(240,67,67,0.3)' : 'var(--border)'}`,
                  }}
                >
                  <div
                    className="text-[9px] font-display font-bold tracking-wider uppercase leading-tight"
                    style={{ color: active ? 'var(--violet)' : 'var(--fg-muted)' }}
                  >
                    {tactic}
                  </div>
                  <div className="text-[9px] font-mono text-fg-dim mt-0.5">
                    {covered}/{ids.length} covered
                  </div>
                </div>
                {/* Technique cells */}
                <div className="space-y-1.5">
                  {ids.map(id => (
                    <TechniqueCell key={id} id={id} meta={TECHNIQUES[id]} hit={coverage[id]} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 flex-wrap text-[10px] font-mono text-fg-muted">
        <span className="text-fg-dim">Cell colour = highest severity mapped to that technique:</span>
        {['critical', 'high', 'medium', 'low'].map(s => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-sm" style={{ background: SEV_COLOR[s], boxShadow: `0 0 4px ${SEV_COLOR[s]}` }} />
            {s}
          </span>
        ))}
        <span className="flex items-center gap-1.5 text-fg-dim">
          <span className="w-2 h-2 rounded-sm" style={{ border: '1px solid var(--border)' }} />
          not observed
        </span>
        <span className="flex items-center gap-1 ml-auto text-fg-dim">
          <ExternalLink size={9} /> cells link to attack.mitre.org
        </span>
      </div>
    </motion.div>
  )
}
