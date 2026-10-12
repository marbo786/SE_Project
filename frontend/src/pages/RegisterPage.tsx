import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Terminal, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function RegisterPage() {
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await authApi.register(form)
      localStorage.setItem('token', res.data.access_token)
      localStorage.setItem('user', JSON.stringify(res.data.user))
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Account registration failed. Please verify inputs.')
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
            New Operator Registration
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
            <Label htmlFor="name" className="text-xs text-[#A1A1AA] font-mono">
              OPERATOR NAME
            </Label>
            <Input
              id="name"
              type="text"
              placeholder="e.g. Alex Mercer"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
              autoComplete="name"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="email" className="text-xs text-[#A1A1AA] font-mono">
              EMAIL ADDRESS
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="user@organization.domain"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              required
              autoComplete="email"
              disabled={loading}
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
                value={form.password}
                onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                required
                autoComplete="new-password"
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
            Create Operator Account
          </Button>
        </form>

        <div className="pt-2 border-t border-[#303136] text-center text-xs text-[#777981]">
          <span>Existing operator? </span>
          <Link
            to="/login"
            className="text-[#7895B5] hover:text-[#96B2D1] font-mono hover:underline"
          >
            Sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
