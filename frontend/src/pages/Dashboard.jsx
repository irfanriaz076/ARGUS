import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Target, Bug, CheckCircle2, Zap, ChevronRight, TrendingUp } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { useEngagements, useFindingsCount } from '../hooks/useEngagement'
import HoloCard from '../components/HoloCard'
import AnimatedNumber from '../components/AnimatedNumber'

const stagger = {
  container: { hidden: {}, show: { transition: { staggerChildren: 0.07 } } },
  item:      { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } } },
}

const STATUS_COLOR = {
  created:  '#584444',
  running:  '#CC0000',
  paused:   '#F5C842',
  complete: '#FFAA33',
}

function StatCard({ icon: Icon, label, value, color, sub }) {
  return (
    <motion.div variants={stagger.item}>
      <HoloCard glowColor={`${color}30`} className="hud-card">
        <div className="flex items-start justify-between gap-3">
          <div
            className="w-10 h-10 flex items-center justify-center flex-shrink-0 rounded-sm"
            style={{
              border: `1px solid ${color}40`,
              background: `${color}10`,
            }}
          >
            <Icon size={18} style={{ color }} />
          </div>
          <TrendingUp size={14} className="text-fg-dim mt-0.5 flex-shrink-0" />
        </div>
        <div className="mt-3">
          <AnimatedNumber
            value={value}
            className="text-3xl font-display font-black leading-none block tabular-nums"
            style={{ color, textShadow: `0 0 10px ${color}50` }}
          />
          <div className="text-[11px] font-display tracking-wider text-fg-muted uppercase mt-1.5">{label}</div>
          {sub && <div className="text-[11px] font-mono text-fg-dim mt-1">{sub}</div>}
          <div
            className="mt-3 h-0.5 w-full rounded-full"
            style={{ background: `linear-gradient(90deg, ${color} 0%, ${color}22 60%, transparent 100%)` }}
          />
        </div>
      </HoloCard>
    </motion.div>
  )
}

function Radar({ engagements }) {
  const rings = [1, 0.75, 0.5, 0.25]
  const blips = engagements.slice(0, 8).map((e, i) => {
    const angle = (i / 8) * Math.PI * 2
    const r     = 0.3 + (i % 3) * 0.15
    return {
      x: 50 + Math.cos(angle) * r * 50,
      y: 50 + Math.sin(angle) * r * 50,
      status: e.status,
    }
  })

  return (
    <div className="relative w-48 h-48 mx-auto">
      {rings.map((r, i) => (
        <div
          key={i}
          className="absolute rounded-full"
          style={{
            border: '1px solid rgba(204,0,0,0.15)',
            inset: `${(1 - r) * 50}%`,
          }}
        />
      ))}
      <div className="absolute inset-0 flex items-center">
        <div className="w-full h-px" style={{ background: 'rgba(204,0,0,0.1)' }} />
      </div>
      <div className="absolute inset-0 flex justify-center">
        <div className="h-full w-px" style={{ background: 'rgba(204,0,0,0.1)' }} />
      </div>
      <div className="absolute inset-0 rounded-full overflow-hidden animate-radar-sweep origin-center">
        <div
          style={{
            width: '100%', height: '100%',
            background: 'conic-gradient(from 0deg, transparent 0deg, rgba(204,0,0,0.25) 45deg, transparent 45deg)',
          }}
        />
      </div>
      {blips.map((b, i) => (
        <motion.div
          key={i}
          className="absolute w-1.5 h-1.5 rounded-full"
          style={{
            left: `${b.x}%`, top: `${b.y}%`,
            transform: 'translate(-50%,-50%)',
            background: STATUS_COLOR[b.status] ?? '#CC0000',
            boxShadow: `0 0 5px ${STATUS_COLOR[b.status] ?? '#CC0000'}`,
          }}
          animate={{ opacity: [1, 0.25, 1] }}
          transition={{ duration: 2.5 + i * 0.4, repeat: Infinity, ease: 'easeInOut' }}
        />
      ))}
      <div
        className="absolute w-2.5 h-2.5 rounded-full"
        style={{
          left: '50%', top: '50%', transform: 'translate(-50%,-50%)',
          background: '#CC0000',
          boxShadow: '0 0 8px #CC0000, 0 0 16px rgba(204,0,0,0.4)',
        }}
      />
    </div>
  )
}

const CustomTooltip = ({ active, payload }) =>
  active && payload?.length ? (
    <div
      className="font-mono text-[12px] px-3 py-2"
      style={{ background: '#100809', border: '1px solid #261414', borderRadius: '2px' }}
    >
      <span style={{ color: payload[0].payload.fill }}>{payload[0].name}</span>
      <span className="text-fg-muted ml-2">{payload[0].value}</span>
    </div>
  ) : null

export default function Dashboard() {
  const { data: engagements = [], isLoading } = useEngagements()
  const { data: countData } = useFindingsCount()

  const total    = engagements.length
  const running  = engagements.filter(e => e.status === 'running').length
  const complete = engagements.filter(e => e.status === 'complete').length
  const created  = engagements.filter(e => e.status === 'created').length

  const statusData = Object.entries(
    engagements.reduce((a, e) => ({ ...a, [e.status]: (a[e.status] ?? 0) + 1 }), {})
  ).map(([name, value]) => ({ name, value, fill: STATUS_COLOR[name] ?? '#505075' }))

  if (isLoading) return (
    <div className="flex items-center gap-2.5 text-fg-muted text-[13px] font-mono pt-10">
      <div className="w-2 h-2 bg-neon-green rounded-full animate-neon-pulse" />
      Initializing ARGUS...
    </div>
  )

  return (
    <motion.div variants={stagger.container} initial="hidden" animate="show" className="space-y-6">

      {/* Page header */}
      <motion.div variants={stagger.item} className="space-y-1.5">
        <div className="flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-neon-green animate-neon-pulse flex-shrink-0"
            style={{ boxShadow: '0 0 8px rgba(204,0,0,0.9)' }} />
          <h1 className="font-display font-black text-2xl md:text-3xl text-gradient-red tracking-wider">
            THREAT INTELLIGENCE HUB
          </h1>
        </div>
        <p className="text-[12px] font-mono text-fg-muted tracking-widest">
          Autonomous Attack Surface Orchestration · ARGUS v2.0
        </p>
        <div
          className="h-px w-56"
          style={{ background: 'linear-gradient(90deg,var(--green),rgba(204,0,0,0) 70%)' }}
        />
      </motion.div>

      {/* Stat cards */}
      <motion.div variants={stagger.container} className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          icon={Shield}
          label="Total Engagements"
          value={total}
          color="#CC0000"
          sub={total === 0 ? 'None yet' : `${created} pending`}
        />
        <StatCard
          icon={Zap}
          label="Active Scans"
          value={running}
          color="#FFAA33"
          sub={running > 0 ? 'Live now' : 'All idle'}
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={complete}
          color="#F04343"
          sub={total > 0 ? `${Math.round((complete/total)*100)}% done` : '—'}
        />
        <StatCard
          icon={Bug}
          label="Findings"
          value={countData?.total ?? '—'}
          color="#F5C842"
          sub="Across all scans"
        />
      </motion.div>

      {/* Main panels */}
      <motion.div variants={stagger.container} className="grid md:grid-cols-2 gap-5">

        {/* Radar */}
        <motion.div variants={stagger.item}>
          <HoloCard glowColor="rgba(204,0,0,0.15)" className="hud-card" corners>
            <div className="section-label green">Engagement Radar</div>
            <Radar engagements={engagements} />
            <div className="mt-4 grid grid-cols-4 gap-2 text-center border-t border-border pt-4">
              {Object.entries(STATUS_COLOR).map(([s, c]) => (
                <div key={s}>
                  <div
                    className="text-[11px] font-display tracking-wider"
                    style={{ color: c }}
                  >
                    {s.toUpperCase()}
                  </div>
                  <div
                    className="text-xl font-display font-black mt-0.5"
                    style={{ color: c, textShadow: `0 0 8px ${c}50` }}
                  >
                    {engagements.filter(e => e.status === s).length}
                  </div>
                </div>
              ))}
            </div>
          </HoloCard>
        </motion.div>

        {/* Pie + recents */}
        <motion.div variants={stagger.item} className="flex flex-col gap-4">
          <HoloCard glowColor="rgba(255,170,51,0.15)" className="hud-card" corners>
            <div className="section-label cyan">Status Distribution</div>
            {statusData.length === 0 ? (
              <div className="text-center py-8 text-fg-muted text-[13px] font-mono">
                No engagement data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie
                    data={statusData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={62}
                    paddingAngle={3}
                  >
                    {statusData.map((e, i) => (
                      <Cell key={i} fill={e.fill} stroke="transparent" />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </HoloCard>

          <HoloCard glowColor="rgba(240,67,67,0.15)" className="hud-card flex-1" corners>
            <div className="flex items-center justify-between mb-3">
              <div className="section-label violet" style={{ marginBottom: 0 }}>Recent Engagements</div>
              <Link to="/engagements" className="text-[11px] font-mono neon-cyan hover:underline leading-none">
                VIEW ALL →
              </Link>
            </div>
            {engagements.length === 0 ? (
              <div className="text-center py-5">
                <p className="text-fg-muted text-[13px] font-mono mb-4">
                  No engagements found. Initialize one to begin.
                </p>
                <Link to="/engagements" className="btn-cyber">
                  + NEW ENGAGEMENT
                </Link>
              </div>
            ) : (
              <div className="space-y-1">
                {engagements.slice(0, 5).map(eng => {
                  const sc = STATUS_COLOR[eng.status] ?? '#584444'
                  return (
                    <Link key={eng.id} to={`/engagements/${eng.id}`}>
                      <motion.div
                        className="flex items-center gap-3 py-2 px-2 rounded-sm hover:bg-white/[0.04] transition-colors cursor-pointer"
                        whileHover={{ x: 3 }}
                        transition={{ duration: 0.15 }}
                      >
                        <div
                          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                          style={{ background: sc, boxShadow: `0 0 4px ${sc}` }}
                        />
                        <span className="text-[13px] font-mono text-fg flex-1 truncate">{eng.name}</span>
                        <span
                          className="text-[10px] font-display tracking-wider px-1.5 py-0.5 flex-shrink-0"
                          style={{
                            color: sc,
                            border: `1px solid ${sc}35`,
                            background: `${sc}0D`,
                          }}
                        >
                          {eng.status.toUpperCase()}
                        </span>
                        <ChevronRight size={12} className="text-fg-dim flex-shrink-0" />
                      </motion.div>
                    </Link>
                  )
                })}
              </div>
            )}
          </HoloCard>
        </motion.div>

      </motion.div>
    </motion.div>
  )
}
