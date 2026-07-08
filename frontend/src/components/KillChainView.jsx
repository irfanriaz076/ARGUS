import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Check, Loader, ChevronDown, ChevronRight,
  Clock, Shield, AlertTriangle, Info, Zap,
  Search, Globe, Camera, ScrollText, Satellite, Github,
  ClipboardList, Radar, FolderSearch, Radiation, Eye, Syringe,
  FolderGit2, Blocks, Lock, KeyRound, FolderOpen, ShieldAlert, Network,
  Wrench,
} from 'lucide-react'
import { useKillChain } from '../hooks/useEngagement'
import SeverityBadge from './SeverityBadge'

const STAGE_META = {
  recon:            { color: '#00FFCC', label: 'RECON',        desc: 'Passive discovery & surface mapping' },
  enumeration:      { color: '#FFAA33', label: 'ENUM',         desc: 'Active port & service enumeration' },
  vulnerability:    { color: '#CC0000', label: 'VULN',         desc: 'Vulnerability detection & CVE matching' },
  exploitation:     { color: '#FF44AA', label: 'EXPLOIT',      desc: 'Active exploitation & proof-of-concept' },
  post_exploitation:{ color: '#9944FF', label: 'POST-EXPLOIT', desc: 'Post-exploitation: TLS, credentials, data' },
}

// Red-team palette accents only (matches the rest of ARGUS) — rotated per tool
// so icons stay visually distinguishable without reintroducing off-brand hues.
const PALETTE = ['#CC0000', '#FFAA33', '#F04343', '#FF2020', '#F5C842', '#FF5522']

const TOOL_ICON = {
  subfinder:            { Icon: Search,         color: PALETTE[1] },
  httpx_probe:          { Icon: Globe,          color: PALETTE[2] },
  gowitness_screenshot: { Icon: Camera,         color: PALETTE[4] },
  crtsh_enum:           { Icon: ScrollText,     color: PALETTE[1] },
  shodan_lookup:        { Icon: Satellite,      color: PALETTE[2] },
  github_dorking:       { Icon: Github,         color: PALETTE[3] },
  whois_asn:            { Icon: ClipboardList,  color: PALETTE[4] },
  nmap_scanner:         { Icon: Radar,          color: PALETTE[0] },
  ffuf_fuzzer:          { Icon: FolderSearch,   color: PALETTE[5] },
  nuclei_scanner:       { Icon: Radiation,      color: PALETTE[0] },
  nikto_scanner:        { Icon: Eye,            color: PALETTE[2] },
  sqlmap_scanner:       { Icon: Syringe,        color: PALETTE[3] },
  git_exposure:         { Icon: FolderGit2,     color: PALETTE[5] },
  dalfox_scanner:       { Icon: Zap,            color: PALETTE[4] },
  wpscan_lite:          { Icon: Blocks,         color: PALETTE[1] },
  testssl_scanner:      { Icon: Lock,           color: PALETTE[2] },
  hydra_brute:          { Icon: KeyRound,       color: PALETTE[3] },
  sensitive_files:      { Icon: FolderOpen,     color: PALETTE[5] },
  header_analyzer:      { Icon: ShieldAlert,    color: PALETTE[2] },
  cors_tester:          { Icon: Network,        color: PALETTE[0] },
}

function duration(s) {
  if (!s) return null
  if (s < 60) return `${s.toFixed(1)}s`
  return `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

function StatusDot({ status, color }) {
  if (status === 'done') return (
    <div className="w-6 h-6 rounded-sm flex items-center justify-center"
      style={{ border: `1px solid ${color}`, background: `${color}18`, boxShadow: `0 0 8px ${color}40` }}>
      <Check size={12} style={{ color }} />
    </div>
  )
  if (status === 'active') return (
    <motion.div className="w-6 h-6 rounded-sm flex items-center justify-center"
      style={{ border: `1px solid ${color}`, background: `${color}12` }}
      animate={{ boxShadow: [`0 0 4px ${color}40`, `0 0 14px ${color}70`, `0 0 4px ${color}40`] }}
      transition={{ duration: 1.6, repeat: Infinity }}>
      <Loader size={11} style={{ color }} className="animate-spin" />
    </motion.div>
  )
  if (status === 'failed') return (
    <div className="w-6 h-6 rounded-sm flex items-center justify-center"
      style={{ border: '1px solid #CC0000', background: '#CC000018' }}>
      <AlertTriangle size={11} color="#CC0000" />
    </div>
  )
  return (
    <div className="w-6 h-6 rounded-sm flex items-center justify-center"
      style={{ border: '1px solid #2a1a1a', background: '#1a0e0e' }}>
      <div className="w-1.5 h-1.5 rounded-full bg-border" />
    </div>
  )
}

function ToolRow({ tool, stageColor }) {
  const [open, setOpen] = useState(false)
  const dur = duration(tool.duration_s)
  const statusColor = tool.status === 'complete' ? stageColor
    : tool.status === 'running' ? '#FFAA33'
    : tool.status === 'failed'  ? '#CC0000'
    : '#2a1a1a'
  const { Icon: ToolIcon, color: toolColor } = TOOL_ICON[tool.name] ?? { Icon: Wrench, color: '#886868' }

  return (
    <div className="border border-border rounded overflow-hidden"
      style={{ background: 'rgba(10,5,5,0.6)' }}>
      <button
        onClick={() => tool.finding_count > 0 && setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div
          className="w-6 h-6 flex-shrink-0 flex items-center justify-center rounded-sm"
          style={{ border: `1px solid ${toolColor}35`, background: `${toolColor}12` }}
        >
          <ToolIcon size={12} style={{ color: toolColor }} />
        </div>
        <span className="flex-1 font-mono text-[12px] text-fg">{tool.name}</span>

        {dur && (
          <span className="flex items-center gap-1 text-[10px] font-mono text-fg-dim">
            <Clock size={9} />{dur}
          </span>
        )}

        <span className="text-[10px] font-display tracking-wide px-1.5 py-0.5 rounded"
          style={{ color: statusColor, border: `1px solid ${statusColor}40`, background: `${statusColor}0D` }}>
          {tool.status.toUpperCase()}
        </span>

        {tool.finding_count > 0 && (
          <span className="flex items-center gap-1 text-[11px] font-display ml-1"
            style={{ color: stageColor }}>
            {tool.finding_count}
            {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
          </span>
        )}
        {tool.finding_count === 0 && (
          <span className="text-[10px] text-fg-dim font-mono ml-1">0</span>
        )}
      </button>

      <AnimatePresence>
        {open && tool.findings.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <div className="border-t border-border px-3 py-2 space-y-1.5">
              {tool.findings.map(f => (
                <div key={f.id} className="flex items-center gap-2">
                  <SeverityBadge severity={f.severity} />
                  <span className="text-[11px] font-mono text-fg-muted truncate">{f.title}</span>
                </div>
              ))}
              {tool.finding_count > tool.findings.length && (
                <p className="text-[10px] text-fg-dim font-mono pl-1">
                  +{tool.finding_count - tool.findings.length} more findings…
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function StageCard({ stage, idx }) {
  const [open, setOpen] = useState(stage.status !== 'idle')
  const meta  = STAGE_META[stage.id] ?? { color: '#666', label: stage.label, desc: '' }
  const color = meta.color

  return (
    <div className="relative">
      {/* Stage card */}
      <motion.div
        className="rounded border overflow-hidden"
        style={{
          borderColor: stage.status === 'idle' ? '#1a0e0e' : `${color}35`,
          background: stage.status === 'idle' ? 'rgba(10,5,5,0.4)' : `rgba(10,5,5,0.7)`,
        }}
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: idx * 0.08, duration: 0.3 }}
      >
        {/* Stage header */}
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
        >
          <StatusDot status={stage.status} color={color} />

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2.5">
              <span className="font-display font-black text-[13px] tracking-widest"
                style={{ color: stage.status === 'idle' ? '#3a2020' : color }}>
                {meta.label}
              </span>
              {stage.status !== 'idle' && (
                <span className="text-[10px] font-mono text-fg-dim">{meta.desc}</span>
              )}
            </div>
          </div>

          {stage.status !== 'idle' && (
            <div className="flex items-center gap-3 flex-shrink-0">
              {stage.tools.length > 0 && (
                <span className="text-[10px] text-fg-dim font-mono">
                  {stage.tools.length} tool{stage.tools.length !== 1 ? 's' : ''}
                </span>
              )}
              {stage.finding_count > 0 && (
                <span className="text-[12px] font-display font-bold px-2 py-0.5 rounded"
                  style={{ color, border: `1px solid ${color}40`, background: `${color}12` }}>
                  {stage.finding_count} finding{stage.finding_count !== 1 ? 's' : ''}
                </span>
              )}
              {open
                ? <ChevronDown size={13} className="text-fg-dim" />
                : <ChevronRight size={13} className="text-fg-dim" />}
            </div>
          )}
        </button>

        {/* Stage body */}
        <AnimatePresence>
          {open && stage.status !== 'idle' && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="border-t px-4 py-3 space-y-2"
                style={{ borderColor: `${color}20` }}>
                {stage.tools.length === 0 ? (
                  <p className="text-[12px] text-fg-dim font-mono">No tools ran in this stage.</p>
                ) : (
                  stage.tools.map(t => (
                    <ToolRow key={t.scan_id} tool={t} stageColor={color} />
                  ))
                )}

                {/* Discoveries summary */}
                {stage.discoveries.length > 0 && (
                  <div className="mt-3 pt-2 border-t flex flex-wrap gap-2"
                    style={{ borderColor: `${color}20` }}>
                    {stage.discoveries.map((d, i) => (
                      <span key={i}
                        className="text-[10px] font-mono px-2 py-1 rounded"
                        style={{ color, border: `1px solid ${color}30`, background: `${color}0A` }}>
                        ↳ {d}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Connector arrow between stages */}
      {idx < 3 && (
        <div className="flex flex-col items-center py-1 my-1 relative">
          <div className="w-px h-5" style={{
            background: stage.status === 'done'
              ? `linear-gradient(to bottom, ${color}, ${STAGE_META[['recon','enumeration','vulnerability','exploitation'][idx+1]]?.color ?? '#333'})`
              : '#1a0e0e',
          }} />
          {stage.status === 'done' && stage.discoveries.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute left-1/2 -translate-x-1/2 top-0.5 whitespace-nowrap"
              style={{ color: `${color}99` }}
            >
            </motion.div>
          )}
          <div className="w-0 h-0" style={{
            borderLeft: '4px solid transparent',
            borderRight: '4px solid transparent',
            borderTop: `5px solid ${stage.status === 'done' ? STAGE_META[['recon','enumeration','vulnerability','exploitation'][idx+1]]?.color ?? color : '#1a0e0e'}`,
          }} />
        </div>
      )}
    </div>
  )
}

export default function KillChainView({ engagementId, isRunning }) {
  const { data, isLoading } = useKillChain(engagementId, isRunning)

  if (isLoading) return (
    <div className="flex items-center gap-2.5 text-fg-muted text-[13px] font-mono py-8">
      <Loader size={14} className="animate-spin" />
      Loading kill chain…
    </div>
  )

  if (!data) return null

  const { stages, total_findings, total_targets, severity_counts = {} } = data

  return (
    <div className="space-y-4">

      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Targets',  val: total_targets,  color: '#00FFCC', icon: Shield },
          { label: 'Findings', val: total_findings, color: '#CC0000', icon: AlertTriangle },
          { label: 'Critical', val: severity_counts.critical ?? 0, color: '#CC0000', icon: Zap },
          { label: 'High',     val: severity_counts.high ?? 0,     color: '#CC5500', icon: Info },
        ].map(({ label, val, color, icon: Icon }) => (
          <div key={label} className="hud-card flex items-center gap-3"
            style={{ borderColor: `${color}25` }}>
            <Icon size={16} style={{ color, flexShrink: 0 }} />
            <div>
              <div className="text-[18px] font-display font-black" style={{ color }}>{val}</div>
              <div className="text-[9px] font-display tracking-widest text-fg-dim">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Kill chain flow */}
      <div className="max-w-2xl">
        {stages.map((stage, idx) => (
          <StageCard key={stage.id} stage={stage} idx={idx} />
        ))}
      </div>
    </div>
  )
}
