import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { historyApi, apiError } from '@/lib/api'
import { Button } from '@/components/ui/button'

export function ProjectWorkspace({ id, name, archived, saved }: { id: number; name: string; archived?: boolean; saved: () => Promise<unknown> }) {
  const [title, setTitle] = useState(name)
  const cache = useQueryClient()
  const revisions = useQuery({ queryKey: ['revisions', id], queryFn: async () => (await historyApi.revisions(id)).data })
  const action = useMutation({ mutationFn: (work: () => Promise<unknown>) => work(), onSuccess: async () => { await saved(); await cache.invalidateQueries({ queryKey: ['projects'] }); await cache.invalidateQueries({ queryKey: ['archived-projects'] }) } })
  return <details className="border rounded p-4 print:hidden"><summary className="cursor-pointer font-semibold">Project details and revision timeline</summary>
    <div className="space-y-4 mt-4">
      <form onSubmit={e => { e.preventDefault(); action.mutate(() => historyApi.rename(id, { name: title, expected_name: name })) }} className="flex flex-wrap items-end gap-3">
        <label className="flex-1">Project name<input className="block w-full rounded border bg-secondary p-2" required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} /></label>
        <Button disabled={action.isPending || archived || !title.trim()}>Save name</Button>
      </form>
      <Button variant="outline" disabled={action.isPending} onClick={() => action.mutate(() => historyApi.lifecycle(id, archived ? 'restore' : 'archive'))}>{archived ? 'Restore project' : 'Archive project'}</Button>
      {action.isError && <p role="alert">{apiError(action.error)}</p>}
      {action.isSuccess && <p role="status">Project updated.</p>}
      <h3 className="font-semibold">Revision timeline</h3>
      {revisions.isPending ? <p role="status">Loading revisions…</p> : revisions.isError ? <p role="alert">{apiError(revisions.error)} <button onClick={() => revisions.refetch()}>Retry</button></p> : <ol className="space-y-2">{revisions.data.items.map(revision => <li key={revision.id}><Link className="underline text-primary" to={`/projects/${id}/revisions/${revision.id}`}>Revision {revision.number} — {revision.state}</Link><span> · {revision.artifacts.length} sources · {revision.analysis_profile?.replace(/_/g, ' ') || 'Legacy scope'}</span></li>)}</ol>}
      {(revisions.data?.total || 0) > 100 && <p>Showing the newest 100 revisions.</p>}
    </div>
  </details>
}
