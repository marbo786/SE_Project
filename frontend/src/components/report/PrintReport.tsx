import type { Project, Finding, TraceLink } from './types'
import type { RunSummary } from '@/lib/api'

export function PrintReport({ project, run, findings, links, reviews, warnings }: { project: Project; run?: RunSummary | null; findings: Finding[]; links: TraceLink[]; reviews: { finding_id?: number; status: string }[]; warnings: string[] }) {
  return <section className="hidden print-report" aria-label="Complete printable report">
    <h1>{project.name} — Revision {project.version}</h1>
    <p>Run {run?.id || 'No analysis'} · {run?.status} · {run?.created_at}</p>
    <h2>Scope and quality score</h2>
    <p>{project.quality_score?.details?.profile || project.analysis_profile} · {project.analysis_mode} · Rubric {project.quality_score?.details?.rubric_version || 'unknown'}</p>
    <p>Overall: {project.quality_score?.overall_score == null ? 'Not graded' : `${project.quality_score.overall_score.toFixed(1)} / 100`}</p>
    <p>{project.quality_score?.details?.note}</p>
    {Object.entries(project.quality_score?.details?.categories || {}).map(([key, value]) => <p key={key}>{key}: {!value.applicable ? 'Not applicable' : value.percentage == null ? 'Not evaluated' : `${value.percentage.toFixed(1)}%`}; eligible {value.eligible_count}; weight {value.weight}%; contribution {value.contribution ?? 'not evaluated'}</p>)}
    {Object.entries(project.quality_score?.details?.ai_coverage || {}).map(([key, value]) => <p key={key}>{key}: {value.reviewed}/{value.total} reviewed. {value.note}</p>)}
    {warnings.map((warning, index) => <p key={index}>{warning}</p>)}
    <h2>All findings ({findings.length})</h2>
    {findings.map(finding => <article key={finding.id}><h3>{finding.severity} · {finding.rule_id} · {finding.requirement_id}</h3><p>{finding.explanation}</p><p>Source: {finding.source_ref || 'Not recorded'}</p><p>{finding.quoted_text}</p><p>Review: {reviews.find(review => review.finding_id === finding.id)?.status || 'needs review'}</p>{finding.rewrite_suggestion && <><p>Proposed text (human review required): {finding.rewrite_suggestion}</p><p>{finding.rewrite_semantic_review?.explanation}</p></>}</article>)}
    <h2>All trace links ({links.length})</h2>
    {links.map(link => <article key={link.id}><h3>{link.source_label || link.source_id} → {link.target_label || link.target_id}</h3><p>{link.source_type} → {link.target_type}; {link.is_stale ? 'stale' : link.status}; {link.origin}</p><p>Similarity: {link.confidence ?? 'not measured'} (not a probability)</p><p>Evidence: {JSON.stringify(link.evidence || {})}</p></article>)}
  </section>
}
