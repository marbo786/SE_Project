import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { apiError, historyApi } from '@/lib/api'

export function FindingDecision({ runId, findingId, decision, saved }: { runId: string; findingId: number; decision?: { id: number; status: string }; saved: () => Promise<unknown> }) {
  const [reason, setReason] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  async function submit(status: 'needs_review' | 'accepted' | 'dismissed') {
    setBusy(true); setError('')
    try { await historyApi.decision(runId, { target_type: 'finding', target_id: findingId, status, reason, expected_decision_id: decision?.id || 0 }); await saved() }
    catch (err) { setError(apiError(err)) } finally { setBusy(false) }
  }
  return <section aria-label="Finding decision" className="space-y-2 print:hidden">
    <p>Review: {(decision?.status || 'needs_review').replace(/_/g, ' ')}. Decisions do not change the published score.</p>
    <label className="block">Review note<input className="w-full border rounded bg-background p-2" maxLength={4000} value={reason} onChange={e => setReason(e.target.value)} /></label>
    <div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy} onClick={() => submit('accepted')}>Accept finding</Button><Button variant="outline" disabled={busy} onClick={() => submit('dismissed')}>Dismiss finding</Button>{decision && <Button variant="outline" disabled={busy} onClick={() => submit('needs_review')}>Reset review</Button>}</div>
    {error && <p role="alert">{error}</p>}
  </section>
}
