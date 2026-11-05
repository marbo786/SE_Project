import type { SourceRequirement } from './SourcePanel'

export function TextDiff({ before, after }: { before: string; after: string }) {
  const left = before.split(/(\s+)/), right = after.split(/(\s+)/)
  let start = 0, end = 0
  while (start < Math.min(left.length, right.length) && left[start] === right[start]) start++
  while (end < Math.min(left.length, right.length) - start && left[left.length - 1 - end] === right[right.length - 1 - end]) end++
  return <p className="whitespace-pre-wrap">{left.slice(0, start).join('')}<del className="text-danger">{left.slice(start, left.length - end).join('')}</del>{' '}<ins className="text-success">{right.slice(start, right.length - end).join('')}</ins>{end ? right.slice(right.length - end).join('') : ''}</p>
}
export function RevisionDiff({ requirements }: { requirements: { added: SourceRequirement[]; deleted: SourceRequirement[]; changed: { before: SourceRequirement; after: SourceRequirement }[] } }) {
  return <section aria-label="Requirement changes" className="space-y-4">
    <h2 className="text-lg font-semibold">Requirement changes</h2>
    {requirements.changed.map((item, i) => <article key={i} className="p-4 border rounded"><h3>Changed: {item.after.id || item.after.internal_id}</h3><TextDiff before={item.before.text} after={item.after.text} /><p className="text-muted-foreground">{item.after.source_ref}</p></article>)}
    {(['added', 'deleted'] as const).map(kind => requirements[kind].map((item, i) => <article key={`${kind}-${i}`} className="p-4 border rounded"><h3>{kind === 'added' ? 'Added' : 'Removed'}: {item.id || item.internal_id}</h3><p>{item.text}</p><p>{item.source_ref}</p></article>))}
  </section>
}
