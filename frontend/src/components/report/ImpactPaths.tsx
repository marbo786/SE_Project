import { useMemo } from 'react'
import type { TraceLink } from './types'

export function ImpactPaths({ links, changedIds }: { links: TraceLink[]; changedIds: string[] }) {
  const paths = useMemo(() => {
    const rows: { root: string; path: TraceLink[] }[] = []
    for (const root of changedIds) {
      const seen = new Set([`requirement:${root}`])
      const queue: { type: string; id: string; path: TraceLink[] }[] = [{ type: 'requirement', id: root, path: [] }]
      for (let index = 0; index < queue.length; index++) {
        const node = queue[index]
        for (const link of links.filter(link => !link.is_stale && link.status !== 'rejected' && link.source_type === node.type && link.source_id === node.id)) {
          const key = `${link.target_type}:${link.target_id}`
          if (seen.has(key)) continue
          seen.add(key)
          const path = [...node.path, link]
          rows.push({ root, path }); queue.push({ type: link.target_type, id: link.target_id, path })
        }
      }
    }
    return rows
  }, [links, changedIds])
  return <section aria-label="Architecture impact paths" className="space-y-3 border rounded p-4">
    <h2 className="font-semibold">Architecture impact paths</h2>
    <p className="text-muted-foreground">Paths from changed requirements in this report. Suggested links indicate possible impact; rejected and stale links are excluded.</p>
    {!paths.length ? <p>No current paths were found for these changes. This does not establish that architecture is unaffected.</p> : <ul className="space-y-3">{paths.map(({ root, path }, index) => <li key={`${root}:${index}`}>
      <p>{path[0].source_label || root} {path.map(link => `→ ${link.target_label || link.target_id}`).join(' ')}</p>
      <p className="text-sm text-muted-foreground">{path.every(link => link.status === 'confirmed') ? 'Confirmed path' : 'Contains suggested links'}</p>
      <details><summary className="cursor-pointer">Path evidence</summary>{path.map(link => <p key={link.id} className="break-words">{link.source_label || link.source_id} → {link.target_label || link.target_id}: {JSON.stringify(link.evidence || { origin: link.origin })}</p>)}</details>
    </li>)}</ul>}
  </section>
}
