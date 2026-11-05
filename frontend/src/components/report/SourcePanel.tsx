import { historyApi } from '@/lib/api'
import type { Finding } from './types'

export interface SourceRequirement { internal_id: string; id?: string; text: string; source_ref?: string; artifact_id?: number; class?: string; original_text?: string }
export function SourcePanel({ finding, requirements, projectId }: { finding: Finding; requirements: SourceRequirement[]; projectId: number }) {
  const source = requirements.find(item => item.internal_id === finding.element_id)
  const artifactId = source?.artifact_id || finding.source_spans?.find(span => span.artifact_id)?.artifact_id
  return <section aria-label="Source evidence" className="border rounded p-4 bg-secondary space-y-2">
    <h3 className="font-semibold">Source evidence</h3>
    <p className="text-muted-foreground">{source?.source_ref || finding.source_ref || 'No source location was recorded for this finding.'}</p>
    <blockquote className="whitespace-pre-wrap border-l-2 border-primary pl-3">{source?.text || finding.quoted_text || finding.explanation}</blockquote>
    {source?.class && <p>Classification: {source.class.replace(/_/g, ' ')}</p>}
    {artifactId && <a className="underline text-primary" href={historyApi.source(projectId, artifactId)}>Download original source</a>}
  </section>
}
