import { createContext, useContext, useEffect, useState } from 'react'
import { authApi } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(() => {
    try { return JSON.parse(localStorage.getItem('argus_user')) } catch { return null }
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('argus_token')
    if (!token) { setLoading(false); return }
    authApi.me()
      .then(u => setUser(u))
      .catch(() => { localStorage.removeItem('argus_token'); localStorage.removeItem('argus_user') })
      .finally(() => setLoading(false))
  }, [])

  const login = async (username, password) => {
    const data = await authApi.login({ username, password })
    localStorage.setItem('argus_token', data.access_token)
    localStorage.setItem('argus_user', JSON.stringify({ username: data.username, role: data.role }))
    setUser({ username: data.username, role: data.role })
    return data
  }

  const logout = () => {
    localStorage.removeItem('argus_token')
    localStorage.removeItem('argus_user')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
