import type { Project } from './types'
export function ScoreSummary({ project }: { project: Project }) {
  if (!project.quality_score) return null
  return <section aria-label="Quality score" className="rounded border border-border bg-card p-4 space-y-3">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="font-semibold">{project.quality_score.details?.profile === 'architecture' ? 'Requirements and architecture' : 'Requirements'} assessment</h2>
          <p className="text-2xl font-semibold">{project.quality_score.overall_score == null ? 'Not graded' : `${project.quality_score.overall_score.toFixed(1)} / 100`}</p>
        </div>
        {project.quality_score.details ? <>
          <div className="grid sm:grid-cols-3 gap-4">{Object.entries(project.quality_score.details.categories).map(([name, category]) => <div key={name}>
            <h3 className="capitalize text-sm text-muted-foreground">{name}</h3>
            <p>{!category.applicable ? 'Not applicable' : category.percentage == null ? 'Not evaluated' : `${category.percentage.toFixed(1)}%`}</p>
            {category.applicable && <p className="text-sm text-muted-foreground">{category.eligible_count} eligible · {category.weight}% weight · {category.contribution == null ? 'no contribution' : `${category.contribution.toFixed(1)} points`}</p>}
          </div>)}</div>
          <p className="text-sm text-muted-foreground">{project.quality_score.details.note} Rubric {project.quality_score.details.rubric_version}; {project.analysis_mode} mode.</p>
        </> : <p className="text-sm text-amber-300">Legacy score: this result predates the current rubric and is not comparable to new assessments.</p>}
      </section>
}
