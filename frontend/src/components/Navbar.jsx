import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Target, LayoutDashboard, Bug, Activity, Settings, LogOut, Shield } from 'lucide-react'
import GlitchText from './GlitchText'
import ArgusLogo from './ArgusLogo'
import { useAuth } from '../context/AuthContext'

const LINKS = [
  { to: '/',            label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/engagements', label: 'Engagements', icon: Target },
  { to: '/findings',    label: 'Findings',    icon: Bug },
]

export default function Navbar() {
  const { pathname }    = useLocation()
  const { user, logout } = useAuth()

  return (
    <nav
      className="sticky top-0 z-50 border-b border-border"
      style={{
        background: 'rgba(9,8,10,0.88)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent 0%, rgba(204,0,0,0.55) 30%, rgba(255,170,51,0.3) 70%, transparent 100%)' }}
      />

      <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 select-none group">
          <ArgusLogo size="sm" animated />
          <span
            className="text-[10px] font-mono tracking-wider text-fg-dim border border-border px-1.5 py-0.5 leading-none"
            style={{ clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)' }}
          >
            v2.0
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex gap-0.5">
          {LINKS.map(({ to, label, icon: Icon }) => {
            const active = to === '/' ? pathname === '/' : pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className="relative px-3 py-2.5 rounded-sm group"
              >
                <span
                  className={`flex items-center gap-1.5 text-[13px] font-mono tracking-wide transition-colors duration-200 ${
                    active ? 'neon-cyan' : 'text-fg-muted hover:text-fg'
                  }`}
                >
                  <Icon size={13} />
                  {label}
                </span>
                {active && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute bottom-0 left-2 right-2 h-px"
                    style={{ background: 'var(--cyan)', boxShadow: '0 0 5px var(--cyan)' }}
                    transition={{ type: 'spring', bounce: 0.15, duration: 0.4 }}
                  />
                )}
              </Link>
            )
          })}
        </div>

        {/* Right */}
        <div className="ml-auto flex items-center gap-2 text-[12px] font-mono">
          {/* Status */}
          <div className="flex items-center gap-1.5 text-fg-dim mr-2">
            <Activity size={11} />
            <span>SYS</span>
            <span className="neon-green">ONLINE</span>
            <div
              className="w-1.5 h-1.5 rounded-full bg-neon-green ml-0.5 animate-neon-pulse"
              style={{ boxShadow: '0 0 6px rgba(204,0,0,0.85)' }}
            />
          </div>

          {/* User pill */}
          {user && (
            <div className="flex items-center gap-1 px-2 py-1 text-[10px]"
              style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)' }}>
              <Shield size={10} style={{ color: user.role === 'admin' ? '#FF2020' : '#FFAA33' }} />
              <span className="text-fg-muted">{user.username}</span>
            </div>
          )}

          {/* Settings */}
          <Link to="/settings"
            className="p-2 text-fg-dim hover:text-fg transition-colors"
            title="Settings"
            style={{ opacity: pathname === '/settings' ? 1 : 0.6 }}>
            <Settings size={14} style={{ color: pathname === '/settings' ? 'var(--cyan)' : undefined }} />
          </Link>

          {/* Logout */}
          <button onClick={logout}
            className="p-2 text-fg-dim hover:text-red-500 transition-colors"
            title="Logout">
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </nav>
  )
}
