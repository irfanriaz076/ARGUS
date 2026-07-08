import { Outlet } from 'react-router-dom'
import ParticleField from './ParticleField'
import Navbar from './Navbar'

export default function Layout() {
  return (
    <div className="min-h-screen bg-void relative scanlines">
      {/* HUD grid backdrop */}
      <div className="hud-grid pointer-events-none fixed inset-0 z-0" />

      <ParticleField />

      {/* Ambient glow — subtle, not overwhelming */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(ellipse 70% 45% at 50% -5%, rgba(204,0,0,0.08) 0%, transparent 55%),' +
            'radial-gradient(ellipse 50% 35% at 92% 85%, rgba(255,170,51,0.05) 0%, transparent 55%),' +
            'radial-gradient(ellipse 60% 50% at 8% 100%, rgba(240,67,67,0.04) 0%, transparent 55%)',
        }}
      />

      {/* Edge vignette for focus */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{ boxShadow: 'inset 0 0 220px 40px rgba(0,0,0,0.65)' }}
      />

      <div className="relative z-20 flex flex-col min-h-screen">
        <Navbar />
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
