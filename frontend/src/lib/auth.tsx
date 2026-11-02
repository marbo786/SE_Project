import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { authApi, apiError } from './api'

interface User { id: number; name: string; email: string; email_verified: boolean }
interface AuthContextType {
  user: User | null
  loading: boolean
  error: string
  login: (user: User) => void
  logout: () => Promise<void>
  refresh: () => Promise<void>
  isAuthenticated: boolean
}
const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const generation = useRef(0)
  const cache = useQueryClient()
  const refresh = useCallback(async () => {
    const current = ++generation.current
    setLoading(true)
    setError('')
    try {
      const response = await authApi.getMe()
      if (current === generation.current) setUser(response.data)
    } catch (err: any) {
      if (current === generation.current) {
        if (err.response?.status === 401) setUser(null)
        else setError(apiError(err, 'Unable to check your session. Check your connection and try again.'))
      }
    } finally {
      if (current === generation.current) setLoading(false)
    }
  }, [])
  useEffect(() => {
    // Remove credentials left by versions that used localStorage.
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    void refresh()
    const expired = () => { setUser(null); cache.clear() }
    window.addEventListener('session-expired', expired)
    return () => { ++generation.current; window.removeEventListener('session-expired', expired) }
  }, [refresh, cache])
  const login = (newUser: User) => {
    ++generation.current
    cache.clear()
    setUser(newUser)
    setError('')
    setLoading(false)
  }
  const logout = async () => {
    await authApi.logout()
    ++generation.current
    cache.clear()
    setUser(null)
  }
  return <AuthContext.Provider value={{ user, loading, error, login, logout, refresh, isAuthenticated: !!user }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
