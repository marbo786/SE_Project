import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { historyApi, apiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import type { ManualTrace as ManualTraceInput } from '@/lib/generated-api'

export function ManualTrace({ runId, saved }: { runId: string; saved: () => Promise<unknown> }) {
  const query = useQuery({ queryKey: ['trace-endpoints', runId], queryFn: async () => (await historyApi.endpoints(runId)).data })
  const [source, setSource] = useState(''), [target, setTarget] = useState(''), [reason, setReason] = useState('')
  const mutation = useMutation({ mutationFn: async () => {
    const from = query.data!.find(item => JSON.stringify([item.type, item.id]) === source)!
    const to = query.data!.find(item => JSON.stringify([item.type, item.id]) === target)!
    return historyApi.manualTrace(runId, { source_type: from.type, source_id: from.id, target_type: to.type, target_id: to.id, reason } as ManualTraceInput)
  }, onSuccess: async () => { setReason(''); await saved() } })
  return <details className="border rounded p-4"><summary className="cursor-pointer">Add a manual trace link</summary><form className="grid sm:grid-cols-2 gap-3 mt-3" onSubmit={e => { e.preventDefault(); mutation.mutate() }}>
    {(['source', 'target'] as const).map(side => <label key={side} className="min-w-0">{side === 'source' ? 'Source element' : 'Target element'}<select className="block w-full border rounded p-2 bg-secondary" required value={side === 'source' ? source : target} onChange={e => side === 'source' ? setSource(e.target.value) : setTarget(e.target.value)}><option value="">Choose an element</option>{query.data?.filter(item => side === 'source' ? item.type !== 'class' : item.type !== 'requirement').map(item => <option key={JSON.stringify([item.type, item.id])} value={JSON.stringify([item.type, item.id])}>{item.type}: {item.label}</option>)}</select></label>)}
    <label className="sm:col-span-2">Source evidence<textarea className="block w-full border rounded p-2 bg-secondary" required maxLength={4000} value={reason} onChange={e => setReason(e.target.value)} /></label>
    <p className="sm:col-span-2 text-muted-foreground">Manual links are review annotations. Published scores stay unchanged. Reject a link to remove it from accepted paths.</p>
    <Button disabled={mutation.isPending || !source || !target || !reason.trim()}>Add confirmed link</Button>
    {query.isError && <p role="alert">{apiError(query.error)} <button type="button" onClick={() => query.refetch()}>Retry</button></p>}
    {mutation.isError && <p role="alert">{apiError(mutation.error)}</p>}{mutation.isSuccess && <p role="status">Link saved.</p>}
  </form></details>
}
