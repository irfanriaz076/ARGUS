import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Save, Key, Bell, Users, Shield, Plus, UserX,
  CheckCircle, AlertCircle, Eye, EyeOff,
} from 'lucide-react'
import { authApi, settingsApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

function Section({ icon: Icon, title, children }) {
  return (
    <div className="hud-card space-y-4">
      <div className="flex items-center gap-2 pb-3 border-b border-border">
        <Icon size={13} className="text-fg-muted" />
        <span className="text-[11px] font-display tracking-widest text-fg-muted">{title}</span>
      </div>
      {children}
    </div>
  )
}

function SettingRow({ label, settingKey, value, isSecret, configured, onChange }) {
  const [show, setShow] = useState(false)
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[11px] font-mono text-fg-muted">{label}</span>
          {configured
            ? <span className="text-[10px] text-neon-green font-mono">● configured</span>
            : <span className="text-[10px] text-fg-dim font-mono">○ not set</span>}
        </div>
        <div className="relative">
          <input
            type={isSecret && !show ? 'password' : 'text'}
            placeholder={configured ? '••••••••' : 'Enter value…'}
            className="w-full px-3 py-2 bg-transparent font-mono text-[12px] text-fg outline-none"
            style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: '2px' }}
            onChange={e => onChange(settingKey, e.target.value)}
            onFocus={e => e.target.style.borderColor = 'rgba(204,0,0,0.5)'}
            onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
          {isSecret && (
            <button
              type="button"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-fg-dim"
              onClick={() => setShow(s => !s)}
            >
              {show ? <EyeOff size={13} /> : <Eye size={13} />}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Settings() {
  const { user }           = useAuth()
  const [settings, setSets] = useState([])
  const [changes, setChanges] = useState({})
  const [saving, setSaving]   = useState(false)
  const [saved, setSaved]     = useState(false)
  const [users, setUsers]     = useState([])
  const [newUser, setNewUser] = useState({ username: '', email: '', password: '', role: 'viewer' })
  const [userSaving, setUS]   = useState(false)
  const [userMsg, setUserMsg] = useState('')

  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    settingsApi.list().then(setSets).catch(() => {})
    if (isAdmin) authApi.listUsers().then(setUsers).catch(() => {})
  }, [isAdmin])

  const handleChange = (key, val) => setChanges(c => ({ ...c, [key]: val }))

  const save = async () => {
    const toSave = Object.fromEntries(Object.entries(changes).filter(([, v]) => v.trim()))
    if (!Object.keys(toSave).length) return
    setSaving(true)
    try {
      await settingsApi.update(toSave)
      setSaved(true)
      setChanges({})
      settingsApi.list().then(setSets)
      setTimeout(() => setSaved(false), 3000)
    } finally {
      setSaving(false)
    }
  }

  const createUser = async e => {
    e.preventDefault()
    setUS(true); setUserMsg('')
    try {
      const u = await authApi.createUser(newUser)
      setUsers(us => [...us, u])
      setNewUser({ username: '', email: '', password: '', role: 'viewer' })
      setUserMsg(`User '${u.username}' created`)
    } catch (err) {
      setUserMsg(err.response?.data?.detail || 'Error creating user')
    } finally {
      setUS(false)
    }
  }

  const deactivate = async (id, name) => {
    if (!confirm(`Deactivate ${name}?`)) return
    try {
      const u = await authApi.deactivateUser(id)
      setUsers(us => us.map(x => x.id === id ? u : x))
    } catch (err) {
      alert(err.response?.data?.detail || 'Error')
    }
  }

  const API_KEY_SETTINGS = [
    { key: 'shodan_api_key',    label: 'Shodan API Key',       desc: 'Enables IP/host intelligence (shodan.io)' },
    { key: 'github_token',      label: 'GitHub Token',         desc: 'Increases GitHub dorking rate limit (30→30/min)' },
    { key: 'nvd_api_key',       label: 'NVD API Key',          desc: 'Faster CVE enrichment (10 req/s vs 5/30s)' },
    { key: 'wpscan_api_key',    label: 'WPScan API Key',       desc: 'WordPress CVE database lookup (50 req/day free)' },
  ]
  const NOTIFY_SETTINGS = [
    { key: 'slack_webhook_url', label: 'Slack Webhook URL',    desc: 'Slack Incoming Webhook for critical finding alerts' },
    { key: 'webhook_url',       label: 'Generic Webhook URL',  desc: 'POST JSON alerts to any endpoint' },
    { key: 'notify_on_critical',label: 'Alert on Critical',    desc: 'Send alert for every critical finding (true/false)', isSecret: false },
    { key: 'notify_on_high',    label: 'Alert on High',        desc: 'Send alert for every high finding (true/false)', isSecret: false },
  ]

  const getS = key => settings.find(s => s.key === key) || { key, value: '', is_secret: true, configured: false }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-display tracking-widest neon-red">SETTINGS</h1>
        <p className="text-fg-muted text-[12px] font-mono mt-1">
          Platform configuration, API keys, notifications, and user management
        </p>
      </div>

      {/* API Keys */}
      <Section icon={Key} title="API KEY INTEGRATIONS">
        <div className="space-y-4">
          {API_KEY_SETTINGS.map(({ key, label, desc }) => {
            const s = getS(key)
            return (
              <div key={key}>
                <SettingRow
                  label={label}
                  settingKey={key}
                  value={s.value}
                  isSecret
                  configured={s.configured}
                  onChange={handleChange}
                />
                <p className="text-[10px] text-fg-dim font-mono mt-1 ml-0">{desc}</p>
              </div>
            )
          })}
        </div>
      </Section>

      {/* Notifications */}
      <Section icon={Bell} title="NOTIFICATIONS">
        <div className="space-y-4">
          {NOTIFY_SETTINGS.map(({ key, label, desc, isSecret = true }) => {
            const s = getS(key)
            return (
              <div key={key}>
                <SettingRow
                  label={label}
                  settingKey={key}
                  value={s.value}
                  isSecret={isSecret}
                  configured={s.configured}
                  onChange={handleChange}
                />
                <p className="text-[10px] text-fg-dim font-mono mt-1">{desc}</p>
              </div>
            )
          })}
        </div>
      </Section>

      {/* Save button */}
      {isAdmin && (
        <div className="flex items-center gap-3">
          <button
            onClick={save}
            disabled={saving || !Object.keys(changes).length}
            className="flex items-center gap-2 px-5 py-2.5 font-display text-[11px] tracking-widest transition-all"
            style={{
              background: saving ? 'rgba(204,0,0,0.3)' : 'rgba(204,0,0,0.85)',
              border: '1px solid rgba(204,0,0,0.6)',
              color: '#fff',
              opacity: Object.keys(changes).length ? 1 : 0.4,
              cursor: Object.keys(changes).length ? 'pointer' : 'not-allowed',
            }}
          >
            <Save size={13} />
            {saving ? 'SAVING…' : 'SAVE SETTINGS'}
          </button>
          {saved && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-1.5 text-[12px] font-mono text-neon-green"
            >
              <CheckCircle size={13} /> Saved — restart worker to apply API key changes
            </motion.span>
          )}
        </div>
      )}

      {/* User Management (admin only) */}
      {isAdmin && (
        <Section icon={Users} title="USER MANAGEMENT">
          <div className="space-y-3">
            {users.map(u => (
              <div key={u.id} className="flex items-center gap-3 p-3"
                style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <Shield size={13} style={{ color: u.role === 'admin' ? '#FF2020' : '#FFAA33' }} />
                <div className="flex-1">
                  <span className="font-mono text-[13px] text-fg">{u.username}</span>
                  <span className="ml-2 text-[10px] text-fg-muted font-mono">{u.email}</span>
                </div>
                <span className="text-[10px] font-display tracking-widest"
                  style={{ color: u.role === 'admin' ? '#FF2020' : '#FFAA33' }}>
                  {u.role.toUpperCase()}
                </span>
                <span className="text-[10px] font-mono" style={{ color: u.is_active ? '#00FF99' : '#666' }}>
                  {u.is_active ? '● active' : '○ inactive'}
                </span>
                {u.username !== user?.username && u.is_active && (
                  <button onClick={() => deactivate(u.id, u.username)}
                    className="text-fg-dim hover:text-red-500 transition-colors">
                    <UserX size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Create user form */}
          <form onSubmit={createUser} className="pt-3 border-t border-border space-y-3">
            <p className="text-[10px] font-display tracking-widest text-fg-muted">CREATE NEW USER</p>
            <div className="grid grid-cols-2 gap-3">
              {[['username','Username','text'],['email','Email','email'],['password','Password','password']].map(([field, ph, type]) => (
                <input key={field} type={type} placeholder={ph} required
                  value={newUser[field]}
                  onChange={e => setNewUser(n => ({ ...n, [field]: e.target.value }))}
                  className="px-3 py-2 bg-transparent font-mono text-[12px] text-fg outline-none col-span-1"
                  style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: '2px' }}
                />
              ))}
              <select value={newUser.role} onChange={e => setNewUser(n => ({ ...n, role: e.target.value }))}
                className="px-3 py-2 bg-bg font-mono text-[12px] text-fg outline-none"
                style={{ border: '1px solid rgba(255,255,255,0.1)', borderRadius: '2px' }}>
                <option value="viewer">Viewer</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            {userMsg && (
              <p className="text-[11px] font-mono" style={{ color: userMsg.includes('created') ? '#00FF99' : '#FF4444' }}>
                {userMsg}
              </p>
            )}
            <button type="submit" disabled={userSaving}
              className="flex items-center gap-2 px-4 py-2 font-display text-[10px] tracking-widest"
              style={{ background: 'rgba(255,170,51,0.15)', border: '1px solid rgba(255,170,51,0.35)', color: '#FFAA33' }}>
              <Plus size={12} /> {userSaving ? 'CREATING…' : 'CREATE USER'}
            </button>
          </form>
        </Section>
      )}

      {!isAdmin && (
        <div className="flex items-center gap-2 p-4 text-[12px] font-mono"
          style={{ background: 'rgba(255,170,51,0.06)', border: '1px solid rgba(255,170,51,0.2)', color: '#FFAA33' }}>
          <AlertCircle size={13} />
          Settings modification requires admin role.
        </div>
      )}
    </div>
  )
}
