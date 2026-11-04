import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import { authApi, apiError } from '@/lib/api'
import { Button } from '@/components/ui/button'

export default function AccountPage() {
  const { user, refresh } = useAuth()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  async function verify() {
    setBusy(true); setError(''); setMessage('')
    try { const response = await authApi.requestVerification(); setMessage(response.data.message) }
    catch (error) { setError(apiError(error)) }
    finally { setBusy(false) }
  }
  return <section className="max-w-xl space-y-5">
    <h1 className="text-2xl font-semibold">Your account</h1>
    <p>{user?.name}</p><p>{user?.email}</p>
    <p>Email {user?.email_verified ? 'verified' : 'awaiting verification'}</p>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {message && <p role="status">{message}</p>}
    {!user?.email_verified && <div className="flex flex-wrap gap-3">
      <Button disabled={busy} onClick={verify}>{busy ? 'Sending…' : 'Send verification link'}</Button>
      <Button variant="outline" onClick={refresh}>Check verification status</Button>
    </div>}
  </section>
}
