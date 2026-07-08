import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Play, ChevronRight, Clock, X, Target, Trash2 } from 'lucide-react'
import { useEngagements, useCreateEngagement, useStartEngagement, useDeleteEngagement } from '../hooks/useEngagement'
import HoloCard from '../components/HoloCard'
import CyberButton from '../components/CyberButton'

const STATUS_COLOR = {
  created:  '#584444',
  running:  '#CC0000',
  paused:   '#F5C842',
  complete: '#FFAA33',
}

const stagger = {
  c: { hidden: {}, show: { transition: { staggerChildren: 0.06 } } },
  i: { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: 'easeOut' } } },
}

const FIELD_LABEL = 'block text-[10px] font-display tracking-widest text-fg-muted uppercase mb-1.5'

function CreateModal({ onClose }) {
  const [name, setName]   = useState('')
  const [desc, setDesc]   = useState('')
  const [scope, setScope] = useState('')
  const create = useCreateEngagement()

  const submit = async (e) => {
    e.preventDefault()
    const scopeArr = scope.split('\n').map(s => s.trim()).filter(Boolean)
    await create.mutateAsync({ name, description: desc, scope: scopeArr })
    onClose()
  }

  return (
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.15 } }}
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(12px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.93, y: 16, opacity: 0 }}
        animate={{ scale: 1, y: 0, opacity: 1 }}
        exit={{ scale: 0.95, y: 8, opacity: 0 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
        className="w-full max-w-lg"
      >
        <HoloCard className="hud-card" corners>
          <div className="flex items-center justify-between mb-5 pb-3 border-b border-border">
            <h2 className="font-display font-black text-[15px] neon-green tracking-widest">
              NEW ENGAGEMENT
            </h2>
            <button
              onClick={onClose}
              className="text-fg-muted hover:neon-red transition-colors p-1"
              aria-label="Close modal"
            >
              <X size={15} />
            </button>
          </div>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className={FIELD_LABEL}>Engagement Name <span className="neon-red">*</span></label>
              <input
                className="cyber-input"
                placeholder="Client A — External Pentest"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                autoFocus
              />
            </div>
            <div>
              <label className={FIELD_LABEL}>Description</label>
              <input
                className="cyber-input"
                placeholder="Objectives, rules of engagement..."
                value={desc}
                onChange={e => setDesc(e.target.value)}
              />
            </div>
            <div>
              <label className={FIELD_LABEL}>Scope — one entry per line</label>
              <textarea
                className="cyber-input font-mono"
                rows={4}
                placeholder={'*.example.com\n192.168.1.0/24\napi.target.io'}
                value={scope}
                onChange={e => setScope(e.target.value)}
                style={{ resize: 'vertical' }}
              />
              <p className="text-[11px] text-fg-dim mt-1.5 font-mono">
                Wildcards: *.example.com · CIDR: 10.0.0.0/24 · IP: 192.168.1.1
              </p>
            </div>
            <div className="flex gap-3 pt-1">
              <CyberButton type="submit" disabled={create.isPending} className="flex-1">
                {create.isPending ? 'INITIALIZING...' : '+ INITIALIZE'}
              </CyberButton>
              <CyberButton variant="ghost" onClick={onClose} type="button">CANCEL</CyberButton>
            </div>
          </form>
        </HoloCard>
      </motion.div>
    </motion.div>
  )
}

export default function Engagements() {
  const [showCreate, setShowCreate] = useState(false)
  const { data: engagements = [], isLoading } = useEngagements()
  const start = useStartEngagement()
  const del = useDeleteEngagement()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="font-display font-black text-2xl neon-green tracking-wider">
            ENGAGEMENTS
          </h1>
          <p className="text-[12px] font-mono text-fg-muted mt-1">
            {engagements.length} operation{engagements.length !== 1 ? 's' : ''} indexed
          </p>
          <div className="h-px w-40 mt-1.5" style={{ background: 'linear-gradient(90deg,var(--green),transparent)' }} />
        </div>
        <CyberButton onClick={() => setShowCreate(true)}>
          <span className="flex items-center gap-1.5">
            <Plus size={13} /> NEW ENGAGEMENT
          </span>
        </CyberButton>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2.5 text-fg-muted text-[13px] font-mono">
          <div className="w-2 h-2 bg-neon-green rounded-full animate-neon-pulse" />
          Loading engagement database...
        </div>
      )}

      {!isLoading && engagements.length === 0 && (
        <HoloCard className="hud-card text-center py-16" corners>
          <Target size={28} className="mx-auto text-fg-dim mb-4" />
          <p className="text-fg-muted font-mono text-[13px] mb-5">
            No engagements found. Create one to begin reconnaissance.
          </p>
          <CyberButton onClick={() => setShowCreate(true)}>
            + INITIALIZE FIRST ENGAGEMENT
          </CyberButton>
        </HoloCard>
      )}

      <motion.div variants={stagger.c} initial="hidden" animate="show" className="space-y-2.5">
        {engagements.map(eng => {
          const sc = STATUS_COLOR[eng.status] ?? '#584444'
          return (
            <motion.div key={eng.id} variants={stagger.i}>
              <HoloCard
                glowColor={`${sc}20`}
                intensity={0.45}
                className="hud-card group cursor-pointer"
              >
                <Link to={`/engagements/${eng.id}`} className="flex items-center gap-4">
                  {/* Live indicator */}
                  <div className="flex-shrink-0">
                    <motion.div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ background: sc, boxShadow: `0 0 6px ${sc}` }}
                      animate={eng.status === 'running'
                        ? { boxShadow: [`0 0 4px ${sc}`, `0 0 14px ${sc}`, `0 0 4px ${sc}`] }
                        : {}}
                      transition={{ duration: 1.8, repeat: Infinity }}
                    />
                  </div>

                  {/* Name + scope */}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-[14px] text-fg group-hover:neon-cyan transition-colors duration-200 truncate">
                      {eng.name}
                    </div>
                    <div className="text-[11px] text-fg-dim mt-0.5 truncate font-mono">
                      {eng.scope.length > 0 ? eng.scope.join(' · ') : 'No scope defined'}
                    </div>
                  </div>

                  {/* Meta row */}
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-fg-dim font-mono">
                      <Clock size={10} />
                      {new Date(eng.created_at).toLocaleDateString()}
                    </div>

                    <span
                      className="text-[10px] font-display tracking-wider px-2 py-0.5"
                      style={{
                        color: sc,
                        border: `1px solid ${sc}35`,
                        background: `${sc}0D`,
                        clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
                      }}
                    >
                      {eng.status.toUpperCase()}
                    </span>

                    {eng.status === 'created' && (
                      <button
                        onClick={e => { e.preventDefault(); start.mutate(eng.id) }}
                        className="btn-cyber py-1 px-3 flex items-center gap-1.5"
                        style={{ minHeight: '28px', fontSize: '10px' }}
                      >
                        <Play size={10} /> RUN
                      </button>
                    )}

                    <button
                      onClick={e => {
                        e.preventDefault()
                        if (window.confirm(`Delete "${eng.name}"?`)) del.mutate(eng.id)
                      }}
                      className="text-fg-dim hover:text-red-500 transition-colors p-1 opacity-0 group-hover:opacity-100"
                      title="Delete engagement"
                    >
                      <Trash2 size={13} />
                    </button>

                    <ChevronRight size={13} className="text-fg-dim group-hover:text-neon-cyan transition-colors" />
                  </div>
                </Link>
              </HoloCard>
            </motion.div>
          )
        })}
      </motion.div>

      <AnimatePresence>
        {showCreate && <CreateModal onClose={() => setShowCreate(false)} />}
      </AnimatePresence>
    </div>
  )
}
