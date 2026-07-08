import { useState } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import SplashScreen from './components/SplashScreen'
import Dashboard from './pages/Dashboard'
import EngagementDetail from './pages/EngagementDetail'
import Engagements from './pages/Engagements'
import Findings from './pages/Findings'
import GlobalFindings from './pages/GlobalFindings'
import Login from './pages/Login'
import Settings from './pages/Settings'

export default function App() {
  const [booted, setBooted] = useState(false)

  return (
    <>
      {!booted && <SplashScreen onDone={() => setBooted(true)} />}
      {booted && (
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={
                <ProtectedRoute><Layout /></ProtectedRoute>
              }>
                <Route index element={<Dashboard />} />
                <Route path="engagements" element={<Engagements />} />
                <Route path="engagements/:id" element={<EngagementDetail />} />
                <Route path="engagements/:id/findings" element={<Findings />} />
                <Route path="findings" element={<GlobalFindings />} />
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </AuthProvider>
        </BrowserRouter>
      )}
    </>
  )
}
