import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, SlidersHorizontal } from 'lucide-react'
import { useFindings, useEngagement } from '../hooks/useEngagement'
import FindingCard from '../components/FindingCard'
import HoloCard from '../components/HoloCard'
import SeverityBadge from '../components/SeverityBadge'

const SEVERITIES = ['critical', 'high', 'medium', 'low', 'info']
const STATUSES   = ['', 'open', 'confirmed', 'false_positive']
const SEV_ORDER  = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
const SEV_COLOR  = {
  critical: '#FF2020',
  high:     '#FF5522',
  medium:   '#F5C842',
  low:      '#FFAA33',
  info:     '#584444',
}

export default function Findings() {
  const { id }   = useParams()
  const [sev,    setSev]    = useState('')
  const [status, setStatus] = useState('')

  const { data: eng }          = useEngagement(id)
  const { data: findings = [], isLoading } = useFindings(id, {
    ...(sev    && { severity: sev }),
    ...(status && { status }),
  })

  const sorted    = [...findings].sort((a, b) => (SEV_ORDER[a.severity] ?? 5) - (SEV_ORDER[b.severity] ?? 5))
  const sevCounts = findings.reduce((a, f) => ({ ...a, [f.severity]: (a[f.severity] ?? 0) + 1 }), {})

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link
          to={`/engagements/${id}`}
          className="text-fg-dim hover:neon-cyan transition-colors p-1 -ml-1"
          aria-label="Back to engagement"
        >
          <ArrowLeft size={17} />
        </Link>
        <div>
          <h1 className="font-display font-black text-2xl neon-green tracking-wider">
            FINDINGS
          </h1>
          <p className="text-[12px] font-mono text-fg-muted mt-0.5">{eng?.name}</p>
        </div>
        <div
          className="h-px w-32 ml-1"
          style={{ background: 'linear-gradient(90deg,var(--green),transparent)', alignSelf: 'flex-end', marginBottom: '6px' }}
        />
      </div>

      {/* Severity quick filters */}
      {Object.keys(sevCounts).length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSev('')}
            className="text-[11px] font-display tracking-widest px-3 py-1.5 transition-all min-h-[32px]"
            style={{
              border: `1px solid ${sev === '' ? 'var(--green)' : 'var(--border)'}`,
              color: sev === '' ? 'var(--green)' : 'var(--fg-muted)',
              background: sev === '' ? 'rgba(204,0,0,0.06)' : 'transparent',
              clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
            }}
          >
            ALL ({findings.length})
          </button>
          {SEVERITIES.map(s =>
            sevCounts[s] ? (
              <button
                key={s}
                onClick={() => setSev(sev === s ? '' : s)}
                className="flex items-center gap-1.5 px-2 py-1.5 border transition-all min-h-[32px]"
                style={{
                  borderColor: sev === s ? SEV_COLOR[s] : 'var(--border)',
                  color: sev === s ? SEV_COLOR[s] : 'var(--fg-muted)',
                  background: sev === s ? `${SEV_COLOR[s]}10` : 'transparent',
                  clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
                }}
              >
                <SeverityBadge severity={s} />
                <span className="text-[11px] font-mono ml-1">{sevCounts[s]}</span>
              </button>
            ) : null
          )}
        </div>
      )}

      {/* Filter bar */}
      <HoloCard className="hud-card flex items-center gap-4 flex-wrap py-3" corners={false}>
        <div className="flex items-center gap-2 text-[11px] font-display tracking-widest text-fg-muted">
          <SlidersHorizontal size={12} />
          FILTERS
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[11px] font-mono text-fg-muted">Status</label>
          <select
            className="cyber-input"
            style={{ width: 160 }}
            value={status}
            onChange={e => setStatus(e.target.value)}
          >
            {STATUSES.map(s => <option key={s} value={s}>{s || 'All statuses'}</option>)}
          </select>
        </div>

        <span className="ml-auto text-[12px] font-mono text-fg-muted">
          {sorted.length} result{sorted.length !== 1 ? 's' : ''}
        </span>
      </HoloCard>

      {isLoading && (
        <div className="flex items-center gap-2.5 text-fg-muted text-[13px] font-mono">
          <div className="w-2 h-2 bg-neon-green rounded-full animate-neon-pulse" />
          Querying findings database...
        </div>
      )}

      {!isLoading && sorted.length === 0 && (
        <HoloCard className="hud-card text-center py-12" corners>
          <p className="text-fg-muted text-[13px] font-mono">No findings match current filters.</p>
        </HoloCard>
      )}

      <div>
        {sorted.map(f => <FindingCard key={f.id} finding={f} />)}
      </div>
    </div>
  )
}
