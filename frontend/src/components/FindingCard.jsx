import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronRight, ExternalLink, Link as LinkIcon,
  Github, Shield, Zap, TrendingUp, AlertTriangle,
  CheckCircle2, XCircle, AlertOctagon, Circle,
} from 'lucide-react'
import HoloCard from './HoloCard'
import SeverityBadge from './SeverityBadge'
import { findingsApi } from '../api/client'

const SEVERITY_GLOW = {
  critical: 'rgba(255,32,32,0.18)',
  high:     'rgba(255,85,34,0.18)',
  medium:   'rgba(245,200,66,0.15)',
  low:      'rgba(255,170,51,0.15)',
  info:     'rgba(88,68,68,0.1)',
}

const CVSS_COLOR = (score) => {
  if (!score) return '#584444'
  if (score >= 9)  return '#FF2020'
  if (score >= 7)  return '#FF5522'
  if (score >= 4)  return '#F5C842'
  if (score > 0)   return '#FFAA33'
  return '#584444'
}

const EPSS_COLOR = (score) => {
  if (score >= 0.7) return '#FF2020'
  if (score >= 0.3) return '#FF5522'
  if (score >= 0.1) return '#F5C842'
  return '#584444'
}

function Badge({ children, color, title }) {
  return (
    <span
      className="text-[10px] font-display px-1.5 py-0.5 tracking-wider flex-shrink-0 leading-none"
      style={{
        background: `${color}12`,
        border: `1px solid ${color}45`,
        color,
        clipPath: 'polygon(3px 0%,100% 0%,calc(100% - 3px) 100%,0% 100%)',
      }}
      title={title}
    >
      {children}
    </span>
  )
}

function CvssBadge({ score }) {
  if (!score) return null
  return (
    <Badge color={CVSS_COLOR(score)} title={`CVSS Score ${score.toFixed(1)}`}>
      CVSS {score.toFixed(1)}
    </Badge>
  )
}

function EpssBadge({ epss }) {
  if (!epss?.score) return null
  const pct = Math.round(epss.score * 100)
  const col = EPSS_COLOR(epss.score)
  return (
    <span
      className="flex items-center gap-1 text-[10px] font-display px-1.5 py-0.5 flex-shrink-0 leading-none"
      style={{
        background: `${col}12`,
        border: `1px solid ${col}45`,
        color: col,
        clipPath: 'polygon(3px 0%,100% 0%,calc(100% - 3px) 100%,0% 100%)',
      }}
      title={`EPSS: ${pct}% probability of exploitation in wild (${Math.round(epss.percentile * 100)}th percentile)`}
    >
      <TrendingUp size={9} />
      EPSS {pct}%
    </span>
  )
}

function MitreBadge({ technique, mitre }) {
  const id = mitre?.id || technique
  if (!id) return null
  const title = mitre?.name
    ? `MITRE ATT&CK ${id} · ${mitre.name}${mitre.tactic ? ` (${mitre.tactic})` : ''}`
    : `MITRE ATT&CK ${id}`
  return <Badge color="#F04343" title={title}>{id}</Badge>
}

function PocBadge({ count }) {
  if (!count) return null
  return (
    <Badge color="#FF6600" title={`${count} PoC exploit(s) found`}>
      {count} PoC
    </Badge>
  )
}

function EpssBar({ score }) {
  if (!score && score !== 0) return null
  const pct = Math.round(score * 100)
  const col = EPSS_COLOR(score)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-mono">
        <span className="text-fg-muted flex items-center gap-1.5">
          <TrendingUp size={10} style={{ color: col }} />
          Exploitation Probability (EPSS)
        </span>
        <span style={{ color: col }}>{pct}%</span>
      </div>
      <div className="w-full h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: col, boxShadow: `0 0 6px ${col}80` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <p className="text-[10px] text-fg-dim font-mono">
        Top {100 - Math.round((score || 0) * 100)}% most likely to be exploited in the wild
      </p>
    </div>
  )
}

function PocSection({ pocs }) {
  if (!pocs?.length) return null
  return (
    <div>
      <div className="section-label" style={{ color: '#FF6600' }}>
        <span className="flex items-center gap-1.5">
          <AlertTriangle size={10} />
          Proof-of-Concept Exploits ({pocs.length})
        </span>
      </div>
      <div className="space-y-2">
        {pocs.map((poc, i) => (
          <div
            key={i}
            className="flex items-start gap-2.5 p-2.5 rounded"
            style={{ background: 'rgba(255,100,0,0.06)', border: '1px solid rgba(255,100,0,0.2)' }}
          >
            {poc.source === 'github'
              ? <Github size={13} className="flex-shrink-0 mt-0.5" style={{ color: '#FF6600' }} />
              : <Shield size={13} className="flex-shrink-0 mt-0.5" style={{ color: '#FF6600' }} />
            }
            <div className="flex-1 min-w-0">
              <a
                href={poc.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] font-mono hover:underline flex items-center gap-1"
                style={{ color: '#FF6600' }}
                onClick={e => e.stopPropagation()}
              >
                {poc.name}
                <ExternalLink size={9} />
              </a>
              {poc.description && (
                <p className="text-[10px] text-fg-dim font-mono mt-0.5 truncate">
                  {poc.description}
                </p>
              )}
              {poc.stars > 0 && (
                <span className="text-[10px] text-fg-dim font-mono">★ {poc.stars}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const STATUS_CONFIG = {
  open:            { label: 'Open',           color: '#CC0000', icon: Circle },
  remediated:      { label: 'Remediated',     color: '#00FF99', icon: CheckCircle2 },
  accepted_risk:   { label: 'Accepted Risk',  color: '#FFAA33', icon: AlertOctagon },
  false_positive:  { label: 'False Positive', color: '#666699', icon: XCircle },
}

function StatusSelector({ id, current, onChange }) {
  const [saving, setSaving] = useState(false)
  const cfg = STATUS_CONFIG[current] ?? STATUS_CONFIG.open
  const Icon = cfg.icon

  const update = async (status) => {
    if (status === current) return
    setSaving(true)
    try {
      const updated = await findingsApi.update(id, { status })
      onChange(updated.status)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-[10px] font-display tracking-widest text-fg-dim">REMEDIATION:</span>
      {Object.entries(STATUS_CONFIG).map(([key, { label, color, icon: SIcon }]) => (
        <button key={key}
          onClick={e => { e.stopPropagation(); update(key) }}
          disabled={saving}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-display tracking-wider transition-all"
          style={{
            border: `1px solid ${key === current ? color : 'rgba(255,255,255,0.1)'}`,
            background: key === current ? `${color}15` : 'transparent',
            color: key === current ? color : 'rgba(255,255,255,0.3)',
            cursor: saving ? 'not-allowed' : 'pointer',
          }}>
          <SIcon size={10} />
          {label}
        </button>
      ))}
    </div>
  )
}

export default function FindingCard({ finding: initialFinding }) {
  const [open, setOpen]       = useState(false)
  const [finding, setFinding] = useState(initialFinding)
  const nvd  = finding.evidence?.nvd
  const epss = finding.evidence?.epss
  const pocs = finding.evidence?.poc || []
  const isVersionMatch = finding.evidence?.source === 'version_cve_match'
  const proof   = finding.evidence?.proof
  const payload = finding.evidence?.payload
  const filesExposed = finding.evidence?.files_exposed
  const secretPreview = finding.evidence?.secret_preview
  const isExploit = ['sqlmap', 'nikto', 'git_exposure', 'gitleaks'].includes(finding.evidence?.source)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className="mb-2"
    >
      <HoloCard
        glowColor={SEVERITY_GLOW[finding.severity] ?? SEVERITY_GLOW.info}
        intensity={0.5}
        className="hud-card cursor-pointer"
      >
        {/* Header row */}
        <div onClick={() => setOpen(o => !o)}>
          <div className="flex items-center gap-2 flex-wrap">
            <motion.div animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.16 }}>
              <ChevronRight size={12} className="text-fg-dim flex-shrink-0" />
            </motion.div>

            <SeverityBadge severity={finding.severity} />
            <MitreBadge technique={finding.mitre_technique} mitre={finding.evidence?.mitre} />
            <CvssBadge score={finding.cvss_score} />
            <EpssBadge epss={epss} />
            <PocBadge count={pocs.length} />

            {finding.cve_id && (
              <span className="text-[11px] font-mono flex-shrink-0 neon-red">
                {finding.cve_id}
              </span>
            )}

            {isVersionMatch && (
              <Badge color="#00FFCC" title="Found via version-to-CVE matching">
                VERSION MATCH
              </Badge>
            )}

            {isExploit && (
              <Badge color="#FF44AA" title="Active exploitation confirmed">
                EXPLOITED
              </Badge>
            )}

            <span className="text-[13px] text-fg font-mono flex-1 truncate min-w-0">
              {finding.title}
            </span>

            <span className="text-[11px] text-fg-dim font-mono ml-auto flex-shrink-0 tabular-nums">
              {new Date(finding.created_at).toLocaleTimeString()}
            </span>
          </div>

          {!open && finding.description && (
            <p className="text-[12px] text-fg-muted mt-1.5 ml-5 truncate font-mono leading-normal">
              {finding.description}
            </p>
          )}
        </div>

        {/* Expanded detail */}
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="overflow-hidden"
            >
              <div className="mt-4 pt-4 border-t border-border space-y-4">

                {/* Description */}
                <p className="text-[13px] text-fg font-mono leading-relaxed">
                  {nvd?.description || finding.description}
                </p>

                {/* Meta row */}
                <div className="flex flex-wrap gap-5 text-[12px] font-mono">
                  {finding.cve_id && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-fg-muted">CVE:</span>
                      <a
                        href={`https://nvd.nist.gov/vuln/detail/${finding.cve_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="neon-red hover:underline flex items-center gap-1"
                        onClick={e => e.stopPropagation()}
                      >
                        {finding.cve_id} <ExternalLink size={10} />
                      </a>
                    </div>
                  )}
                  {finding.cvss_score != null && (
                    <div>
                      <span className="text-fg-muted">CVSS: </span>
                      <span style={{ color: CVSS_COLOR(finding.cvss_score) }}>
                        {finding.cvss_score.toFixed(1)}
                      </span>
                    </div>
                  )}
                  {nvd?.cvss_vector && (
                    <div>
                      <span className="text-fg-muted">Vector: </span>
                      <span className="text-fg-dim text-[11px]">{nvd.cvss_vector}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-fg-muted">Status: </span>
                    <span style={{ color: STATUS_CONFIG[finding.status]?.color ?? '#00FF99' }}>
                      {finding.status.toUpperCase().replace('_', ' ')}
                    </span>
                  </div>
                  {(finding.evidence?.mitre || finding.mitre_technique) && (
                    <div>
                      <span className="text-fg-muted">ATT&amp;CK: </span>
                      <a
                        href={`https://attack.mitre.org/techniques/${(finding.evidence?.mitre?.id || finding.mitre_technique).replace('.', '/')}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                        style={{ color: '#F04343' }}
                        onClick={e => e.stopPropagation()}
                      >
                        {finding.evidence?.mitre?.id || finding.mitre_technique}
                        {finding.evidence?.mitre?.name ? ` · ${finding.evidence.mitre.name}` : ''}
                      </a>
                      {finding.evidence?.mitre?.tactic && (
                        <span className="text-fg-dim"> ({finding.evidence.mitre.tactic})</span>
                      )}
                    </div>
                  )}
                  {nvd?.published && (
                    <div>
                      <span className="text-fg-muted">Published: </span>
                      <span className="text-fg-dim">{nvd.published}</span>
                    </div>
                  )}
                </div>

                {/* Status selector */}
                <StatusSelector
                  id={finding.id}
                  current={finding.status}
                  onChange={status => setFinding(f => ({ ...f, status }))}
                />

                {/* EPSS bar */}
                {epss && <EpssBar score={epss.score} />}

                {/* Exploitation proof */}
                {proof && (
                  <div>
                    <div className="section-label" style={{ color: '#FF44AA' }}>
                      Proof of Exploitation
                    </div>
                    <pre
                      className="text-[12px] font-mono p-3 leading-relaxed"
                      style={{
                        background: 'rgba(255,68,170,0.06)',
                        border: '1px solid rgba(255,68,170,0.25)',
                        color: '#FF44AA',
                        borderRadius: '2px',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-all',
                      }}
                    >
                      {proof}
                    </pre>
                    {payload && (
                      <pre
                        className="text-[11px] font-mono p-2 mt-1 leading-relaxed"
                        style={{
                          background: 'rgba(255,68,170,0.04)',
                          border: '1px solid rgba(255,68,170,0.15)',
                          color: '#FF88CC',
                          borderRadius: '2px',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-all',
                        }}
                      >
                        Payload: {payload}
                      </pre>
                    )}
                  </div>
                )}

                {/* Exposed files */}
                {filesExposed?.length > 0 && (
                  <div>
                    <div className="section-label" style={{ color: '#FF44AA' }}>
                      Exposed Source Files ({finding.evidence?.file_count ?? filesExposed.length})
                    </div>
                    <div
                      className="p-3 font-mono text-[11px] overflow-y-auto"
                      style={{
                        background: 'rgba(255,68,170,0.05)',
                        border: '1px solid rgba(255,68,170,0.2)',
                        maxHeight: 150,
                        color: '#FF88CC',
                        borderRadius: '2px',
                      }}
                    >
                      {filesExposed.map((f, i) => (
                        <div key={i} className="leading-relaxed">{f}</div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Leaked secret */}
                {secretPreview && (
                  <div>
                    <div className="section-label" style={{ color: '#FF44AA' }}>Leaked Secret (redacted)</div>
                    <code
                      className="block text-[12px] font-mono p-2"
                      style={{
                        background: 'rgba(255,0,0,0.08)',
                        border: '1px solid rgba(255,0,0,0.3)',
                        color: '#FF6666',
                        borderRadius: '2px',
                      }}
                    >
                      {secretPreview}
                    </code>
                  </div>
                )}

                {/* PoC exploits */}
                <PocSection pocs={pocs} />

                {/* Evidence */}
                {finding.evidence && Object.keys(finding.evidence)
                  .filter(k => !['nvd', 'epss', 'poc', 'mitre'].includes(k)).length > 0 && (
                  <div>
                    <div className="section-label cyan">Evidence</div>
                    <pre
                      className="text-[11px] font-mono p-3 overflow-x-auto leading-relaxed"
                      style={{
                        background: 'rgba(0,0,0,0.5)',
                        border: '1px solid rgba(255,170,51,0.15)',
                        color: '#FFAA33',
                        maxHeight: 200,
                        overflowY: 'auto',
                        borderRadius: '2px',
                      }}
                    >
                      {JSON.stringify(
                        Object.fromEntries(
                          Object.entries(finding.evidence)
                            .filter(([k]) => !['nvd', 'epss', 'poc', 'mitre'].includes(k))
                        ),
                        null, 2
                      )}
                    </pre>
                  </div>
                )}

                {/* Patch references */}
                {nvd?.patch_urls?.length > 0 && (
                  <div>
                    <div className="section-label green">Patch References</div>
                    <ul className="space-y-1.5">
                      {nvd.patch_urls.map((url, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <LinkIcon size={10} className="neon-green flex-shrink-0" />
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] font-mono neon-cyan hover:underline truncate"
                            onClick={e => e.stopPropagation()}
                          >
                            {url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* NVD references */}
                {nvd?.references?.length > 0 && (
                  <div>
                    <div className="section-label">NVD References ({nvd.references.length})</div>
                    <ul className="space-y-1 max-h-28 overflow-y-auto">
                      {nvd.references.slice(0, 6).map((url, i) => (
                        <li key={i}>
                          <a
                            href={url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] font-mono text-fg-dim hover:neon-cyan transition-colors truncate block"
                            onClick={e => e.stopPropagation()}
                          >
                            → {url}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </HoloCard>
    </motion.div>
  )
}
