import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { authApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Terminal, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await authApi.login({ email, password })
      login(res.data.access_token, res.data.user)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#111214] flex items-center justify-center p-4 font-sans text-[#E7E7E9]">
      <div className="w-full max-w-sm rounded border border-[#303136] bg-[#1D1E22] p-6 space-y-5">
        {/* Technical Header */}
        <div className="space-y-1.5 border-b border-[#303136] pb-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-5 h-5 rounded-sm bg-[#17181B] border border-[#303136] text-[#7895B5]">
              <Terminal className="h-3 w-3" />
            </div>
            <span className="font-mono text-xs font-semibold tracking-wider text-[#E7E7E9]">
              SRS_REVIEWER
            </span>
          </div>
          <p className="text-xs text-[#777981]">
            System Access Authentication
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            className="p-2.5 rounded border border-[#C04848]/40 bg-[#C04848]/10 text-xs text-[#E06C6C] flex items-start gap-2 font-mono"
            role="alert"
          >
            <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-[#E06C6C]" />
            <span className="leading-tight">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div className="space-y-1">
            <Label htmlFor="email" className="text-xs text-[#A1A1AA] font-mono">
              OPERATOR EMAIL
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="user@organization.domain"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="password" className="text-xs text-[#A1A1AA] font-mono">
              PASSWORD
            </Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                disabled={loading}
                className="pr-8"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#777981] hover:text-[#E7E7E9]"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>

          <Button type="submit" className="w-full mt-2" loading={loading}>
            Authenticate
          </Button>
        </form>

        <div className="pt-2 border-t border-[#303136] text-center text-xs text-[#777981]">
          <span>Unregistered operator? </span>
          <Link
            to="/register"
            className="text-[#7895B5] hover:text-[#96B2D1] font-mono hover:underline"
          >
            Register account
          </Link>
        </div>
      </div>
    </div>
  )
}
