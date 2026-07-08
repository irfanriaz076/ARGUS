import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Shield, Lock, User, AlertTriangle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import ArgusLogo from '../components/ArgusLogo'

export default function Login() {
  const { login }               = useAuth()
  const navigate                = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center"
      style={{ background: '#000000' }}>

      {/* Scan lines */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{ backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.5) 2px, rgba(255,255,255,0.5) 3px)', backgroundSize: '100% 4px' }} />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm px-4"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8 gap-4">
          <ArgusLogo variant="full" size="2xl" animated />
          <p className="text-fg-muted text-[11px] font-mono tracking-[0.28em] uppercase">
            Penetration Testing as a Service
          </p>
        </div>

        {/* Card */}
        <div
          className="p-6 space-y-4"
          style={{
            background: 'rgba(20,8,8,0.95)',
            border: '1px solid rgba(204,0,0,0.3)',
            boxShadow: '0 0 40px rgba(204,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.04)',
          }}
        >
          <div className="flex items-center gap-2 pb-3 border-b border-border">
            <Lock size={13} className="text-fg-muted" />
            <span className="text-[11px] font-display tracking-widest text-fg-muted">OPERATOR AUTHENTICATION</span>
          </div>

          {error && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-2 p-3 text-[12px] font-mono"
              style={{ background: 'rgba(204,0,0,0.12)', border: '1px solid rgba(204,0,0,0.35)', color: '#FF4444' }}
            >
              <AlertTriangle size={12} />
              {error}
            </motion.div>
          )}

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="block text-[10px] font-display tracking-widest text-fg-muted mb-1.5">
                USERNAME
              </label>
              <div className="relative">
                <User size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-dim pointer-events-none" />
                <input
                  type="text"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 bg-transparent font-mono text-[13px] text-fg outline-none"
                  style={{
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '2px',
                    transition: 'border-color 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(204,0,0,0.6)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                  placeholder="admin"
                  autoComplete="username"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-display tracking-widest text-fg-muted mb-1.5">
                PASSWORD
              </label>
              <div className="relative">
                <Lock size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-dim pointer-events-none" />
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2.5 bg-transparent font-mono text-[13px] text-fg outline-none"
                  style={{
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '2px',
                    transition: 'border-color 0.15s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(204,0,0,0.6)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 font-display text-[11px] tracking-widest transition-all duration-150 mt-2"
              style={{
                background: loading ? 'rgba(204,0,0,0.3)' : 'rgba(204,0,0,0.85)',
                border: '1px solid rgba(204,0,0,0.6)',
                color: '#fff',
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'AUTHENTICATING...' : 'AUTHENTICATE'}
            </button>
          </form>
        </div>

        <p className="text-center text-[10px] font-mono text-fg-dim mt-4">
          Default: admin / argus-admin-2025 · Change in Settings
        </p>
      </motion.div>
    </div>
  )
}
