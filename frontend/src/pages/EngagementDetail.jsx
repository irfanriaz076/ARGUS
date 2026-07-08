import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, Plus, Play, Trash2, Target, Bug, Activity, X, Network, FileDown, Crosshair, Sparkles, Grid3x3, RotateCcw } from 'lucide-react'
import {
  useEngagement, useTargets, useScans, useFindings,
  useStartEngagement, useRerunEngagement, useAddTarget, useDeleteTarget,
} from '../hooks/useEngagement'
import TerminalStream from '../components/TerminalStream'
import StageProgress from '../components/StageProgress'
import FindingCard from '../components/FindingCard'
import SeverityBadge from '../components/SeverityBadge'
import HoloCard from '../components/HoloCard'
import CyberButton from '../components/CyberButton'
import AttackGraph from '../components/AttackGraph'
import KillChainView from '../components/KillChainView'
import AttackNarrative from '../components/AttackNarrative'
import TopAttackPath from '../components/TopAttackPath'
import MitreCoverage from '../components/MitreCoverage'
import { reportsApi } from '../api/client'

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }
const TARGET_TYPES = ['domain', 'ip', 'cidr', 'url']

const STATUS_COLOR = {
  created:  '#584444',
  running:  '#CC0000',
  paused:   '#F5C842',
  complete: '#FFAA33',
}

const TABS = [
  { id: 'overview',   label: 'OVERVIEW',    icon: Activity },
  { id: 'killchain',  label: 'KILL CHAIN',  icon: Crosshair },
  { id: 'targets',    label: 'TARGETS',     icon: Target },
  { id: 'findings',   label: 'FINDINGS',    icon: Bug },
  { id: 'graph',      label: 'GRAPH',       icon: Network },
  { id: 'attack',     label: 'ATT&CK',      icon: Grid3x3 },
  { id: 'narrative',  label: 'AI REPORT',   icon: Sparkles },
]

function AddTargetInline({ engId, onClose }) {
  const [value, setValue] = useState('')
  const [type,  setType]  = useState('domain')
  const add = useAddTarget(engId)

  const submit = async (e) => {
    e.preventDefault()
    await add.mutateAsync({ value, type })
    onClose()
  }

  return (
    <motion.form
      onSubmit={submit}
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="hud-card mb-3 flex items-end gap-3 flex-wrap">
        <div className="flex-1 min-w-48">
          <label className="text-[10px] font-display tracking-widest text-fg-muted uppercase block mb-1.5">
            Target
          </label>
          <input
            className="cyber-input"
            placeholder="example.com / 10.0.0.1 / 192.168.0.0/24"
            value={value}
            onChange={e => setValue(e.target.value)}
            required
            autoFocus
          />
        </div>
        <div>
          <label className="text-[10px] font-display tracking-widest text-fg-muted uppercase block mb-1.5">
            Type
          </label>
          <select
            className="cyber-input"
            style={{ width: 110 }}
            value={type}
            onChange={e => setType(e.target.value)}
          >
            {TARGET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <CyberButton type="submit" disabled={add.isPending}>ADD</CyberButton>
        <CyberButton variant="ghost" onClick={onClose} type="button" aria-label="Cancel">
          <X size={13} />
        </CyberButton>
      </div>
    </motion.form>
  )
}

export default function EngagementDetail() {
  const { id } = useParams()
  const [tab, setTab]             = useState('overview')
  const [addTarget, setAddTarget] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [pdfError, setPdfError]         = useState('')

  const exportPdf = async () => {
    setExportingPdf(true)
    setPdfError('')
    try {
      const blob = await reportsApi.pdf(id)
      const url  = window.URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `ARGUS_${(eng?.name || 'report').replace(/\s+/g, '_')}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setPdfError(err.response?.data?.detail || 'PDF export failed.')
    } finally {
      setExportingPdf(false)
    }
  }

  const { data: eng }          = useEngagement(id)
  const { data: targets = [] } = useTargets(id)
  const { data: scans = [] }   = useScans(id)
  const { data: findings = [] }= useFindings(id)
  const start                  = useStartEngagement()
  const rerun                  = useRerunEngagement()
  const deleteTarget           = useDeleteTarget(id)

  const handleRerun = () => {
    const ok = window.confirm(
      'Rerun this engagement? This clears all existing scans and findings and ' +
      'runs the full kill chain again from scratch against the current targets.'
    )
    if (ok) rerun.mutate(id)
  }

  const sorted    = [...findings].sort((a, b) => (SEV_ORDER[a.severity] ?? 5) - (SEV_ORDER[b.severity] ?? 5))
  const sevCounts = findings.reduce((a, f) => ({ ...a, [f.severity]: (a[f.severity] ?? 0) + 1 }), {})

  if (!eng) return (
    <div className="flex items-center gap-2.5 text-fg-muted text-[13px] font-mono pt-10">
      <div className="w-2 h-2 bg-neon-green rounded-full animate-neon-pulse" />
      Loading engagement...
    </div>
  )

  const sc = STATUS_COLOR[eng.status] ?? '#505075'

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-start gap-3">
        <Link
          to="/engagements"
          className="mt-1 text-fg-dim hover:neon-cyan transition-colors p-1 -ml-1"
          aria-label="Back to engagements"
        >
          <ArrowLeft size={17} />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="font-display font-black text-xl neon-green tracking-wider truncate">
            {eng.name}
          </h1>
          <p className="text-[12px] font-mono text-fg-muted mt-0.5 truncate">
            Scope: {eng.scope.length > 0 ? eng.scope.join(' · ') : 'None defined'}
          </p>
        </div>
        <div className="flex items-center gap-2.5 flex-shrink-0">
          <motion.div
            className="flex items-center gap-1.5 text-[12px] font-mono px-3 py-1.5"
            style={{
              color: sc,
              border: `1px solid ${sc}45`,
              background: `${sc}0D`,
              clipPath: 'polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%)',
            }}
            animate={eng.status === 'running'
              ? { boxShadow: [`0 0 6px ${sc}35`, `0 0 16px ${sc}60`, `0 0 6px ${sc}35`] }
              : {}}
            transition={{ duration: 1.8, repeat: Infinity }}
          >
            {eng.status === 'running' && (
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: sc, boxShadow: `0 0 4px ${sc}` }} />
            )}
            {eng.status.toUpperCase()}
          </motion.div>

          {eng.status === 'created' && (
            <CyberButton onClick={() => start.mutate(id)} disabled={start.isPending}>
              <span className="flex items-center gap-1.5">
                <Play size={12} />
                {start.isPending ? 'LAUNCHING...' : 'LAUNCH SCAN'}
              </span>
            </CyberButton>
          )}
          {eng.status === 'complete' && (
            <>
              <CyberButton
                variant="ghost"
                onClick={handleRerun}
                disabled={rerun.isPending}
              >
                <span className="flex items-center gap-1.5">
                  <RotateCcw size={12} className={rerun.isPending ? 'animate-spin' : ''} />
                  {rerun.isPending ? 'RESTARTING...' : 'RERUN'}
                </span>
              </CyberButton>
              <CyberButton
                variant="ghost"
                onClick={exportPdf}
                disabled={exportingPdf}
              >
                <span className="flex items-center gap-1.5">
                  <FileDown size={12} className={exportingPdf ? 'animate-spin' : ''} />
                  {exportingPdf ? 'EXPORTING...' : 'EXPORT PDF'}
                </span>
              </CyberButton>
            </>
          )}
        </div>
      </div>

      {pdfError && (
        <div
          className="text-[12px] font-mono px-3 py-2"
          style={{ color: '#FF2020', border: '1px solid rgba(255,32,32,0.4)', background: 'rgba(255,32,32,0.05)' }}
        >
          {pdfError}
        </div>
      )}

      {rerun.isError && (
        <div
          className="text-[12px] font-mono px-3 py-2"
          style={{ color: '#FF2020', border: '1px solid rgba(255,32,32,0.4)', background: 'rgba(255,32,32,0.05)' }}
        >
          {rerun.error?.response?.data?.detail || 'Rerun failed.'}
        </div>
      )}

      {/* Kill chain pipeline */}
      <HoloCard className="hud-card overflow-x-auto" corners glowColor="rgba(204,0,0,0.12)">
        <div className="section-label" style={{ color: 'var(--fg-dim)' }}>Kill Chain Pipeline</div>
        <StageProgress scans={scans} engagementStatus={eng.status} />
      </HoloCard>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border">
        {TABS.map(({ id: tid, label, icon: Icon }) => (
          <button
            key={tid}
            onClick={() => setTab(tid)}
            className={`relative flex items-center gap-1.5 px-4 py-2.5 text-[11px] font-display tracking-widest transition-colors duration-200 -mb-px ${
              tab === tid ? 'neon-green' : 'text-fg-muted hover:text-fg'
            }`}
          >
            <Icon size={12} />
            {label}
            {tid === 'targets'  && <span className="text-fg-dim ml-0.5">({targets.length})</span>}
            {tid === 'findings' && <span className="text-fg-dim ml-0.5">({findings.length})</span>}
            {tid === 'killchain' && scans.length > 0 && (
              <span className="text-fg-dim ml-0.5">({scans.length})</span>
            )}
            {tab === tid && (
              <motion.div
                layoutId="tab-ind"
                className="absolute bottom-0 left-0 right-0 h-px"
                style={{ background: 'var(--green)', boxShadow: '0 0 5px var(--green)' }}
                transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
              />
            )}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">

        {/* OVERVIEW */}
        {tab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="space-y-5"
          >
            <TopAttackPath engagementId={id} onViewGraph={() => setTab('graph')} />

            <div className="grid md:grid-cols-2 gap-5">
            <div className="space-y-4">
              <TerminalStream engagementId={id} />

              {findings.length > 0 && (
                <HoloCard className="hud-card" glowColor="rgba(255,32,32,0.12)" corners>
                  <div className="section-label red">Finding Summary</div>
                  <div className="flex flex-wrap gap-3">
                    {['critical', 'high', 'medium', 'low', 'info'].map(s =>
                      sevCounts[s] ? (
                        <div key={s} className="flex items-center gap-2">
                          <SeverityBadge severity={s} />
                          <span className="text-xl font-display font-black text-fg">
                            {sevCounts[s]}
                          </span>
                        </div>
                      ) : null
                    )}
                  </div>
                </HoloCard>
              )}
            </div>

            <div className="space-y-4">
              <HoloCard className="hud-card" corners glowColor="rgba(255,170,51,0.12)">
                <div className="section-label cyan">Scan Tasks ({scans.length})</div>
                {scans.length === 0 ? (
                  <p className="text-[13px] text-fg-muted font-mono">No tasks queued.</p>
                ) : (
                  <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
                    {scans.map(scan => {
                      const sc2 = scan.status === 'complete' ? '#FFAA33'
                               : scan.status === 'running'  ? '#CC0000'
                               : scan.status === 'failed'   ? '#FF2020'
                               : '#584444'
                      return (
                        <div key={scan.id} className="flex items-center gap-3 py-1.5 border-b border-border last:border-0">
                          <span className="text-[12px] font-mono text-fg-muted flex-1">{scan.plugin_name}</span>
                          <span className="text-[11px] font-display text-fg-dim">{scan.stage}</span>
                          <span
                            className="text-[11px] font-display tracking-wide"
                            style={{ color: sc2 }}
                          >
                            {scan.status.toUpperCase()}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </HoloCard>

              {sorted.slice(0, 4).length > 0 && (
                <HoloCard className="hud-card" corners glowColor="rgba(245,200,66,0.1)">
                  <div className="flex items-center justify-between mb-3">
                    <div className="section-label yellow" style={{ marginBottom: 0 }}>Top Findings</div>
                    <button
                      onClick={() => setTab('findings')}
                      className="text-[11px] font-mono neon-cyan hover:underline"
                    >
                      ALL →
                    </button>
                  </div>
                  <div className="space-y-0">
                    {sorted.slice(0, 4).map(f => (
                      <div key={f.id} className="flex items-center gap-2.5 py-2 border-b border-border last:border-0">
                        <SeverityBadge severity={f.severity} />
                        <span className="text-[12px] font-mono text-fg truncate">{f.title}</span>
                      </div>
                    ))}
                  </div>
                </HoloCard>
              )}
            </div>
            </div>
          </motion.div>
        )}

        {/* KILL CHAIN */}
        {tab === 'killchain' && (
          <motion.div
            key="killchain"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <KillChainView engagementId={id} isRunning={eng.status === 'running'} />
          </motion.div>
        )}

        {/* TARGETS */}
        {tab === 'targets' && (
          <motion.div
            key="targets"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <div className="flex justify-end mb-3">
              <CyberButton variant="ghost" onClick={() => setAddTarget(t => !t)}>
                <span className="flex items-center gap-1.5"><Plus size={12} /> ADD TARGET</span>
              </CyberButton>
            </div>
            <AnimatePresence>
              {addTarget && <AddTargetInline engId={id} onClose={() => setAddTarget(false)} />}
            </AnimatePresence>

            {targets.length === 0 ? (
              <HoloCard className="hud-card text-center py-12" corners>
                <Target size={26} className="mx-auto text-fg-dim mb-3" />
                <p className="text-fg-muted text-[13px] font-mono">No targets. Add scope to begin.</p>
              </HoloCard>
            ) : (
              <div className="space-y-2">
                {targets.map(t => (
                  <motion.div
                    key={t.id}
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <HoloCard className="hud-card flex items-center gap-3" intensity={0.35} corners={false}>
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{
                          background: t.is_alive ? '#FFAA33' : '#261414',
                          boxShadow: t.is_alive ? '0 0 5px #FFAA33' : 'none',
                        }}
                      />
                      <span className="font-mono text-[13px] text-fg flex-1 truncate">{t.value}</span>
                      <span
                        className="text-[10px] font-display px-1.5 py-0.5"
                        style={{
                          border: '1px solid #261414',
                          color: '#886868',
                          clipPath: 'polygon(3px 0%,100% 0%,calc(100% - 3px) 100%,0% 100%)',
                        }}
                      >
                        {t.type.toUpperCase()}
                      </span>
                      {t.added_by === 'orchestrator' && (
                        <span
                          className="text-[10px] font-display px-1.5 py-0.5"
                          style={{
                            border: '1px solid rgba(240,67,67,0.4)',
                            color: '#F04343',
                            background: 'rgba(240,67,67,0.08)',
                            clipPath: 'polygon(3px 0%,100% 0%,calc(100% - 3px) 100%,0% 100%)',
                          }}
                        >
                          AUTO
                        </span>
                      )}
                      <span
                        className="text-[11px] font-display tracking-wide"
                        style={{ color: t.status === 'complete' ? '#FFAA33' : '#584444' }}
                      >
                        {t.status.toUpperCase()}
                      </span>
                      <button
                        onClick={() => deleteTarget.mutate(t.id)}
                        className="text-fg-dim hover:neon-red transition-colors ml-1 p-1"
                        aria-label="Delete target"
                      >
                        <Trash2 size={12} />
                      </button>
                    </HoloCard>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* FINDINGS */}
        {tab === 'findings' && (
          <motion.div
            key="findings"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            {sorted.length === 0 ? (
              <HoloCard className="hud-card text-center py-14" corners>
                <Bug size={26} className="mx-auto text-fg-dim mb-3" />
                <p className="text-fg-muted text-[13px] font-mono">
                  No findings yet. Launch a scan to discover vulnerabilities.
                </p>
              </HoloCard>
            ) : (
              sorted.map(f => <FindingCard key={f.id} finding={f} />)
            )}
          </motion.div>
        )}

        {/* GRAPH */}
        {tab === 'graph' && (
          <motion.div
            key="graph"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <div className="section-label mb-4">
              D3 Force Attack Surface Graph · Click a path to trace entry → crown jewel
            </div>
            <AttackGraph engagementId={id} />
          </motion.div>
        )}

        {/* ATT&CK COVERAGE */}
        {tab === 'attack' && (
          <motion.div
            key="attack"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <div className="section-label mb-4">
              MITRE ATT&amp;CK Coverage · techniques observed across this engagement
            </div>
            <MitreCoverage findings={findings} />
          </motion.div>
        )}

        {/* AI NARRATIVE */}
        {tab === 'narrative' && (
          <motion.div
            key="narrative"
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
          >
            <AttackNarrative engagementId={id} hasFindings={findings.length > 0} />
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
