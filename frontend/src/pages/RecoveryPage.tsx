import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi, apiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function RecoveryPage({ mode }: { mode: 'request' | 'reset' | 'verify' }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [token] = useState(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get('token') || ''
    return value
  })
  useEffect(() => {
    if (token) window.history.replaceState(null, '', window.location.pathname)
  }, [token])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const title = mode === 'request' ? 'Reset your password' : mode === 'reset' ? 'Choose a new password' : 'Verify your email'
  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const result = mode === 'request' ? await authApi.forgotPassword(email)
        : mode === 'reset' ? await authApi.resetPassword(token, password) : await authApi.verifyEmail(token)
      setMessage(result.data.message)
    } catch (err) { setError(apiError(err)) }
    finally { setBusy(false) }
  }
  return <main className="min-h-screen flex items-center justify-center p-6 bg-[#111214] text-[#E7E7E9]">
    <div className="w-full max-w-md space-y-6 rounded border border-[#303136] bg-[#1D1E22] p-8">
      <h1 className="text-xl font-semibold">{title}</h1>
      {error && <p role="alert" className="text-red-300">{error}</p>}
      {message ? <p role="status">{message}</p> : <form onSubmit={submit} className="space-y-4">
        {mode === 'request' && <div className="space-y-2"><Label htmlFor="email">Email address</Label><Input id="email" type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} /></div>}
        {mode === 'reset' && <div className="space-y-2"><Label htmlFor="password">New password (12–128 characters)</Label><Input id="password" type="password" minLength={12} maxLength={128} autoComplete="new-password" required value={password} onChange={e => setPassword(e.target.value)} /></div>}
        {mode !== 'request' && !token ? <p role="alert">This link has no token. Request a new link.</p> : <Button disabled={busy} type="submit">{busy ? 'Please wait…' : mode === 'verify' ? 'Verify email' : mode === 'request' ? 'Send reset link' : 'Save password'}</Button>}
      </form>}
      <Link className="block text-blue-300 underline" to="/login">Back to sign in</Link>
    </div>
  </main>
}
