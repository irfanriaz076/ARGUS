import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Sparkles, AlertTriangle, ShieldAlert, ListChecks, BookOpen,
  ChevronRight, RefreshCw, Wand2, Settings,
} from 'lucide-react'
import { reportsApi } from '../api/client'
import HoloCard from './HoloCard'

const RATING_COLOR = {
  Critical: '#FF2020', High: '#F04343', Medium: '#F5C842', Low: '#FFAA33',
}
const SEV_COLOR = {
  critical: '#FF2020', high: '#F04343', medium: '#F5C842', low: '#FFAA33', info: '#886868',
}

function SectionTitle({ icon: Icon, color, children }) {
  return (
    <div className="section-label" style={{ color }}>
      <Icon size={12} style={{ color }} />
      {children}
    </div>
  )
}

export default function AttackNarrative({ engagementId, hasFindings }) {
  const [configured, setConfigured] = useState(null)
  const [model, setModel]           = useState('')
  const [report, setReport]         = useState(null)
  const [loading, setLoading]       = useState(false)
  const [error, setError]           = useState('')

  useEffect(() => {
    reportsApi.narrativeStatus()
      .then(d => { setConfigured(d.configured); setModel(d.model || '') })
      .catch(() => setConfigured(false))
  }, [])

  const generate = async () => {
    setLoading(true); setError('')
    try {
      const data = await reportsApi.narrative(engagementId)
      setReport(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed.')
    } finally {
      setLoading(false)
    }
  }

  // ── Not configured ───────────────────────────────────────────────
  if (configured === false) {
    return (
      <HoloCard className="hud-card text-center py-12" corners glowColor="rgba(245,200,66,0.12)">
        <Settings size={26} className="mx-auto text-fg-dim mb-3" />
        <p className="text-fg-muted text-[13px] font-mono mb-2">
          AI narrative is not configured.
        </p>
        <p className="text-fg-dim text-[11px] font-mono max-w-md mx-auto leading-relaxed">
          Add an OpenAI-compatible key to your <span className="neon-yellow">.env</span>:
          set <span className="neon-cyan">LLM_API_KEY</span> (GitHub Models token works),
          and optionally <span className="neon-cyan">LLM_BASE_URL</span> /{' '}
          <span className="neon-cyan">LLM_MODEL</span>. See <span className="neon-yellow">.env.example</span>.
        </p>
      </HoloCard>
    )
  }

  // ── Empty state / generate ───────────────────────────────────────
  if (!report) {
    return (
      <HoloCard className="hud-card text-center py-12" corners glowColor="rgba(204,0,0,0.12)">
        <motion.div
          animate={{ opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2.4, repeat: Infinity }}
        >
          <Wand2 size={30} className="mx-auto neon-red mb-4" />
        </motion.div>
        <p className="text-fg text-[14px] font-display tracking-wider mb-1.5">
          AI ATTACK NARRATIVE
        </p>
        <p className="text-fg-muted text-[12px] font-mono max-w-md mx-auto mb-5 leading-relaxed">
          Synthesize findings, the attack graph, and ranked exploitation paths into a
          red-team engagement story with a full attack chain and remediation.
        </p>
        {!hasFindings && (
          <p className="text-neon-yellow text-[11px] font-mono mb-4">
            Run a scan first — narrative needs findings.
          </p>
        )}
        {error && (
          <p className="text-neon-red text-[11px] font-mono mb-4">{error}</p>
        )}
        <button
          onClick={generate}
          disabled={loading || !hasFindings}
          className="btn-cyber inline-flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading
            ? <><RefreshCw size={13} className="animate-spin" /> GENERATING…</>
            : <><Sparkles size={13} /> GENERATE NARRATIVE</>}
        </button>
        {model && (
          <p className="text-fg-dim text-[10px] font-mono mt-3">model · {model}</p>
        )}
      </HoloCard>
    )
  }

  // ── Report ───────────────────────────────────────────────────────
  const rating = report.risk_rating
  const ratingCol = RATING_COLOR[rating] || '#FFAA33'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          {rating && (
            <span
              className="text-[11px] font-display font-black tracking-wider px-2.5 py-1"
              style={{
                color: ratingCol, border: `1px solid ${ratingCol}55`, background: `${ratingCol}12`,
                clipPath: 'polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%)',
              }}
            >
              {rating.toUpperCase()} RISK
            </span>
          )}
          {report.risk_score != null && (
            <span className="text-[11px] font-mono text-fg-muted">
              SCORE <span className="neon-red">{report.risk_score}</span>
            </span>
          )}
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="btn-cyber-ghost inline-flex items-center gap-1.5"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> REGENERATE
        </button>
      </div>

      {/* Executive summary */}
      {report.executive_summary && (
        <HoloCard className="hud-card" corners glowColor="rgba(204,0,0,0.12)">
          <SectionTitle icon={ShieldAlert} color="var(--red)">Executive Summary</SectionTitle>
          <p className="text-[13px] font-mono text-fg leading-relaxed">
            {report.executive_summary}
          </p>
        </HoloCard>
      )}

      {/* Attack chain */}
      {Array.isArray(report.attack_chain) && report.attack_chain.length > 0 && (
        <HoloCard className="hud-card" corners glowColor="rgba(255,85,34,0.12)">
          <SectionTitle icon={ChevronRight} color="var(--orange)">Attack Chain</SectionTitle>
          <div className="space-y-0">
            {report.attack_chain.map((step, i) => (
              <div key={i} className="flex gap-3 py-2.5 border-b border-border last:border-0">
                <div
                  className="w-6 h-6 flex-shrink-0 flex items-center justify-center text-[11px] font-display font-black rounded-sm"
                  style={{ color: '#FF5522', border: '1px solid rgba(255,85,34,0.4)', background: 'rgba(255,85,34,0.08)' }}
                >
                  {step.step ?? i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[12px] font-display tracking-wide text-fg">{step.title}</span>
                    {step.technique && (
                      <span className="text-[9px] font-mono px-1.5 py-0.5 neon-cyan border border-neon-cyan/40">
                        {step.technique}
                      </span>
                    )}
                    {step.asset && (
                      <span className="text-[10px] font-mono text-fg-dim truncate">{step.asset}</span>
                    )}
                  </div>
                  {step.detail && (
                    <p className="text-[11px] font-mono text-fg-muted mt-1 leading-relaxed">{step.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </HoloCard>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        {/* Key findings */}
        {Array.isArray(report.key_findings) && report.key_findings.length > 0 && (
          <HoloCard className="hud-card" corners glowColor="rgba(240,67,67,0.12)">
            <SectionTitle icon={AlertTriangle} color="var(--violet)">Key Findings</SectionTitle>
            <div className="space-y-2">
              {report.key_findings.map((f, i) => {
                const col = SEV_COLOR[String(f.severity).toLowerCase()] || '#886868'
                return (
                  <div key={i} className="border-b border-border last:border-0 pb-2 last:pb-0">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: col, boxShadow: `0 0 4px ${col}` }} />
                      <span className="text-[12px] font-mono text-fg flex-1">{f.title}</span>
                    </div>
                    {f.impact && (
                      <p className="text-[10px] font-mono text-fg-muted mt-1 ml-3.5 leading-relaxed">{f.impact}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </HoloCard>
        )}

        {/* Recommendations */}
        {Array.isArray(report.recommendations) && report.recommendations.length > 0 && (
          <HoloCard className="hud-card" corners glowColor="rgba(255,170,51,0.12)">
            <SectionTitle icon={ListChecks} color="var(--cyan)">Recommendations</SectionTitle>
            <ul className="space-y-1.5">
              {report.recommendations.map((r, i) => (
                <li key={i} className="flex gap-2 text-[12px] font-mono text-fg-muted leading-relaxed">
                  <ChevronRight size={12} className="neon-cyan flex-shrink-0 mt-0.5" />
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </HoloCard>
        )}
      </div>

      {/* Narrative prose */}
      {report.narrative && (
        <HoloCard className="hud-card" corners glowColor="rgba(204,0,0,0.1)">
          <SectionTitle icon={BookOpen} color="var(--fg-muted)">Engagement Narrative</SectionTitle>
          <p className="text-[13px] font-mono text-fg leading-relaxed whitespace-pre-line">
            {report.narrative}
          </p>
        </HoloCard>
      )}

      <p className="text-fg-dim text-[10px] font-mono text-right">
        Generated by {report.model || 'LLM'} · AI-assisted — verify before reporting
      </p>
    </motion.div>
  )
}
