import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [projects, setProjects] = useState<ProjectItem[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  const user = (() => {
    try {
      return JSON.parse(localStorage.getItem('user') || '{}')
    } catch {
      return {}
    }
  })()

  useEffect(() => {
    let isMounted = true

    Promise.all([
      dashboardApi.getStats().catch(() => ({ data: { total_projects: 0, analyzed_projects: 0, analyzing_projects: 0 } })),
      projectsApi.list().catch(() => ({ data: [] })),
    ])
      .then(([statsRes, projectsRes]) => {
        if (!isMounted) return
        setStats(statsRes.data)
        const projectList = Array.isArray(projectsRes.data) ? projectsRes.data.slice(0, 6) : []
        setProjects(projectList)
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Inspection Dashboard"
        description={user.name ? `Operator: ${user.name} • Active specification review telemetry` : "Active specification review telemetry"}
      >
        <Link to="/projects/new">
          <Button>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            Ingest Specification
          </Button>
        </Link>
      </PageHeader>

      {/* Metrics Strip - Flat, structured summary instead of 3 oversized cards */}
      {loading ? (
        <div className="h-14 rounded border border-[#303136] bg-[#17181B] flex items-center p-4 gap-6">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 rounded border border-[#303136] bg-[#17181B] divide-y sm:divide-y-0 sm:divide-x divide-[#303136]">
          {/* Total Projects */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-mono uppercase tracking-wider text-[#777981]">Total Specifications</p>
              <p className="text-xl font-mono font-semibold text-[#E7E7E9] mt-0.5">
                {stats?.total_projects ?? 0}
              </p>
            </div>
            <span className="text-[10px] font-mono text-[#777981] bg-[#111214] border border-[#303136] px-1.5 py-0.5 rounded">
              INDEXED
            </span>
          </div>

          {/* Analyzed */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#4E8752]" />
                <p className="text-[11px] font-mono uppercase tracking-wider text-[#777981]">Evaluated</p>
              </div>
              <p className="text-xl font-mono font-semibold text-[#E7E7E9] mt-0.5">
                {stats?.analyzed_projects ?? 0}
              </p>
            </div>
            <span className="text-[10px] font-mono text-[#68A86C] bg-[#4E8752]/10 border border-[#4E8752]/30 px-1.5 py-0.5 rounded">
              COMPLETE
            </span>
          </div>

          {/* Analyzing */}
          <div className="p-3.5 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#7895B5]" />
                <p className="text-[11px] font-mono uppercase tracking-wider text-[#777981]">In Analysis</p>
              </div>
              <p className="text-xl font-mono font-semibold text-[#E7E7E9] mt-0.5">
                {stats?.analyzing_projects ?? 0}
              </p>
            </div>
            <span className="text-[10px] font-mono text-[#96B2D1] bg-[#7895B5]/10 border border-[#7895B5]/30 px-1.5 py-0.5 rounded">
              ACTIVE
            </span>
          </div>
        </div>
      )}

      {/* Recent Projects Table */}
      <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden">
        <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-[#303136] bg-[#17181B]">
          <span className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
            Recent Specifications
          </span>
          {projects.length > 0 && (
            <Link
              to="/projects"
              className="text-[11px] font-mono text-[#7895B5] hover:text-[#96B2D1] flex items-center gap-1"
            >
              All Repositories
              <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        {loading ? (
          <SkeletonTable rows={5} cols={5} />
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No specifications indexed"
            description="Upload an SRS document and UML diagrams to run automated requirements verification."
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
                <tr className="border-b border-[#303136] bg-[#141518] text-[10px] font-mono uppercase tracking-wider text-[#777981]">
                  <th className="py-2.5 px-3.5 font-medium">Specification</th>
                  <th className="py-2.5 px-3 font-medium">Revision</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Updated</th>
                  <th className="py-2.5 px-3.5 text-right font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#303136]/50">
                {projects.map((project) => (
                  <tr
                    key={project.id}
                    className="hover:bg-[#24252A]/50 transition-none group"
                  >
                    <td className="py-2.5 px-3.5 max-w-xs">
                      <Link
                        to={`/projects/${project.id}`}
                        className="font-medium text-[#E7E7E9] hover:text-[#7895B5] transition-none block truncate"
                      >
                        {project.name}
                      </Link>
                      {project.description && (
                        <p className="text-[11px] text-[#777981] truncate mt-0.5">
                          {project.description}
                        </p>
                      )}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap font-mono text-[#A1A1AA]">
                      v{project.version || '1'}
                    </td>
                    <td className="py-2.5 px-3 whitespace-nowrap">
                      <span
                        className={cn(
                          "inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-mono border uppercase",
                          statusColor(project.status || 'pending')
                        )}
                      >
                        {project.status || 'pending'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] font-mono text-[#777981] whitespace-nowrap">
                      {project.created_at ? formatRelativeDate(project.created_at) : '—'}
                    </td>
                    <td className="py-2.5 px-3.5 text-right whitespace-nowrap">
                      <Link to={`/projects/${project.id}`}>
                        <Button variant="outline" size="sm" className="h-6 px-2 text-[11px]">
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
