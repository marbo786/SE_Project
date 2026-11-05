import { useProjects, useDashboard } from '@/lib/queries'
import { apiError } from '@/lib/api'
import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { dashboardApi, projectsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/ui/page-header'
import { EmptyState } from '@/components/ui/empty-state'
import { Skeleton, SkeletonTable } from '@/components/ui/skeleton'
import { statusColor, formatRelativeDate, cn } from '@/lib/utils'
import { Plus, ArrowRight, FileText, CheckCircle2, Clock2 } from 'lucide-react'

interface DashboardStats {
  total_projects: number
  analyzed_projects: number
  analyzing_projects: number
}

interface ProjectItem {
  id: string | number
  name: string
  description?: string
  version: string | number
  status: string
  created_at?: string
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const projectsQuery = useProjects(), statsQuery = useDashboard()
  const stats = statsQuery.data as DashboardStats | undefined
  const projects = (projectsQuery.data || []).slice(0, 6) as ProjectItem[]
  const loading = projectsQuery.isPending || statsQuery.isPending
  const { user } = useAuth()
  if (projectsQuery.isError || statsQuery.isError) return <div role="alert" className="space-y-3"><h1>Dashboard unavailable</h1><p>{apiError(projectsQuery.error || statsQuery.error)}</p><Button onClick={() => { void projectsQuery.refetch(); void statsQuery.refetch() }}>Try again</Button></div>

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Review dashboard"
        description={user?.name ? `Welcome, ${user?.name} • Your requirements review workspace` : "Your requirements review workspace"}
      >
        <Link to="/projects/new">
          <Button>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New project
          </Button>
        </Link>
      </PageHeader>

      <details className="border rounded p-4"><summary className="cursor-pointer font-semibold">Try a sample review</summary><ol className="list-decimal pl-6 mt-3 space-y-2"><li><a href="/sample-requirements.docx" className="underline text-primary" download>Download the library SRS sample</a>.</li><li>Create a project with the requirements-only profile and deterministic checks.</li><li>Upload the sample, review extraction, confirm the scope, and analyze.</li><li>Find the ambiguous “respond fast” statement, inspect its source, then edit a new draft and compare the reports.</li></ol><p className="mt-3 text-muted-foreground">Choose thresholds from actual stakeholder needs; the sample does not prescribe a response-time target.</p></details>
      {/* Metrics Strip - Flat, structured summary instead of 3 oversized cards */}
      {loading ? (
        <div className="h-14 rounded border border-border bg-secondary flex items-center p-4 gap-6">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 rounded border border-border bg-secondary divide-y sm:divide-y-0 sm:divide-x divide-border">
          {/* Total Projects */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Total Specifications</p>
              <p className="text-xl font-mono font-semibold text-foreground mt-0.5">
                {stats?.total_projects ?? 0}
              </p>
            </div>
            <span className="text-xs font-mono text-muted-foreground bg-background border border-border px-1.5 py-0.5 rounded">
              INDEXED
            </span>
          </div>

          {/* Analyzed */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-success" />
                <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground">Evaluated</p>
              </div>
              <p className="text-xl font-mono font-semibold text-foreground mt-0.5">
                {stats?.analyzed_projects ?? 0}
              </p>
            </div>
            <span className="text-xs font-mono text-success bg-success/10 border border-success/30 px-1.5 py-0.5 rounded">
              COMPLETE
            </span>
          </div>

          {/* Analyzing */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground">In Analysis</p>
              </div>
              <p className="text-xl font-mono font-semibold text-foreground mt-0.5">
                {stats?.analyzing_projects ?? 0}
              </p>
            </div>
            <span className="text-xs font-mono text-primary bg-primary/10 border border-primary/30 px-1.5 py-0.5 rounded">
              ACTIVE
            </span>
          </div>
        </div>
      )}

      {/* Recent Projects Table */}
      <div className="rounded border border-border bg-card overflow-hidden">
        <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-border bg-secondary">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
            Recent Specifications
          </span>
          {projects.length > 0 && (
            <Link
              to="/projects"
              className="text-xs font-mono text-primary hover:text-primary flex items-center gap-1"
            >
              All projects
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={5} />
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="Start your first review"
            description="Create a project, add your SRS, check the extracted text, then analyze and review the evidence."
            action={{
              label: "New Specification",
              onClick: () => navigate("/projects/new"),
            }}
            className="m-4"
          />
        ) : (
          <div className="overflow-x-auto scrollbar-technical">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-border bg-background text-xs font-mono uppercase tracking-wider text-muted-foreground">
                  <th className="py-2.5 px-3.5 font-medium">Specification</th>
                  <th className="py-2.5 px-3 font-medium">Revision</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Updated</th>
                  <th className="py-2.5 px-3.5 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {projects.map((project) => (
                  <tr
                    key={project.id}
                    className="hover:bg-accent/50 transition-none group"
                  >
                    <td className="py-2.5 px-3.5 max-w-xs">
                      <Link
                        to={`/projects/${project.id}`}
                        className="font-medium text-foreground hover:text-primary transition-none block truncate"
                      >
                        {project.name}
                      </Link>
                      {project.description && (
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {project.description}
                        </p>
                      )}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap font-mono text-muted-foreground">
                      v{project.version || '1'}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-mono border uppercase",
                          statusColor(project.status || 'pending')
                        )}
                      >
                        {project.status || 'pending'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-xs font-mono text-muted-foreground whitespace-nowrap">
                      {project.created_at ? formatRelativeDate(project.created_at) : '—'}
                    </td>
                    <td className="py-2.5 px-3.5 text-right whitespace-nowrap">
                      <Link to={`/projects/${project.id}`}>
                        <Button variant="outline" size="sm" className="h-6 px-2 text-xs">
                          Inspect
                          <ArrowRight className="ml-1 h-3 w-3" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
