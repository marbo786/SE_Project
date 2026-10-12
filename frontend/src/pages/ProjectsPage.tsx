import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SearchInput } from '@/components/ui/input'
import { PageHeader } from '@/components/ui/page-header'
import { EmptyState } from '@/components/ui/empty-state'
import { SkeletonTable } from '@/components/ui/skeleton'
import { Plus, ArrowRight, FolderKanban, Search, RefreshCw } from 'lucide-react'
import { statusColor, formatRelativeDate, formatDate, cn } from '@/lib/utils'

interface Project {
  id: number
  name: string
  description?: string
  version: number | string
  status: string
  created_at?: string
}

type StatusFilter = 'all' | 'done' | 'analyzing' | 'error'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const fetchProjects = () => {
    setLoading(true)
    setError(null)
    projectsApi.list()
      .then(res => {
        setProjects(Array.isArray(res.data) ? res.data : [])
      })
      .catch((err: any) => {
        setError(err.response?.data?.detail || 'Failed to retrieve project list')
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  // Client-side search and status filter
  const filteredProjects = useMemo(() => {
    return projects.filter(p => {
      const matchesSearch =
        search.trim() === '' ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        (p.description && p.description.toLowerCase().includes(search.toLowerCase()))

      const matchesStatus =
        statusFilter === 'all' ||
        p.status?.toLowerCase() === statusFilter.toLowerCase()

      return matchesSearch && matchesStatus
    })
  }, [projects, search, statusFilter])

  // Count by status
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: projects.length, done: 0, analyzing: 0, error: 0 }
    projects.forEach(p => {
      const s = p.status?.toLowerCase()
      if (counts[s] !== undefined) counts[s]++
    })
    return counts
  }, [projects])

  return (
    <div className="space-y-4">
      {/* Header */}
      <PageHeader
        title="Specifications Repository"
        description="Index of analyzed software requirements and architectural traces"
      >
        <Link to="/projects/new">
          <Button>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            New Specification
          </Button>
        </Link>
      </PageHeader>

      {/* Toolbar: Search and Filter */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <SearchInput
            placeholder="Filter by name or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 text-xs"
          />
        </div>

        {/* Filter segment */}
        <div className="flex items-center gap-1 border border-[#303136] rounded p-0.5 bg-[#17181B] text-xs font-mono">
          {(['all', 'done', 'analyzing', 'error'] as const).map(tab => {
            const active = statusFilter === tab
            return (
              <button
                key={tab}
                onClick={() => setStatusFilter(tab)}
                className={cn(
                  "px-2 py-0.5 rounded text-[11px] uppercase transition-none",
                  active
                    ? "bg-[#1D1E22] text-[#E7E7E9] font-medium border border-[#303136]"
                    : "text-[#777981] hover:text-[#A1A1AA]"
                )}
              >
                {tab}
                <span className="ml-1 text-[10px] text-[#777981]">
                  ({statusCounts[tab] ?? 0})
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Table Content */}
      <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden">
        {loading ? (
          <SkeletonTable rows={6} cols={5} />
        ) : error ? (
          <div className="p-8 text-center text-xs text-[#E06C6C] space-y-3">
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchProjects}>
              <RefreshCw className="mr-1.5 h-3 w-3" />
              Retry
            </Button>
          </div>
        ) : projects.length === 0 ? (
          <EmptyState
            icon={FolderKanban}
            title="No specifications available"
            description="Create your first specification project to initiate requirements inspection."
            action={{
              label: "Ingest Specification",
              onClick: () => window.location.href = '/projects/new',
            }}
            className="m-6"
          />
        ) : filteredProjects.length === 0 ? (
          <EmptyState
            icon={Search}
            title="No matching specifications"
            description={`No projects match query "${search}" with status "${statusFilter}".`}
            action={{
              label: "Clear Filters",
              onClick: () => {
                setSearch('')
                setStatusFilter('all')
              },
            }}
            className="m-6"
          />
        ) : (
          <div className="overflow-x-auto scrollbar-technical">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#303136] bg-[#17181B] text-[10px] font-mono uppercase tracking-wider text-[#777981]">
                  <th className="py-2.5 px-3.5 font-medium">Specification Name</th>
                  <th className="py-2.5 px-3 font-medium">Revision</th>
                  <th className="py-2.5 px-3 font-medium">Status</th>
                  <th className="py-2.5 px-3 font-medium">Ingested</th>
                  <th className="py-2.5 px-3.5 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#303136]/50">
                {filteredProjects.map((project) => (
                  <tr
                    key={project.id}
                    className="hover:bg-[#24252A]/50 transition-none group"
                  >
                    <td className="py-2.5 px-3.5 max-w-sm">
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
                          statusColor(project.status)
                        )}
                      >
                        {project.status || 'unknown'}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] font-mono text-[#777981] whitespace-nowrap" title={project.created_at ? formatDate(project.created_at) : undefined}>
                      {project.created_at ? formatRelativeDate(project.created_at) : '—'}
                    </td>
                    <td className="py-2.5 px-3.5 text-right whitespace-nowrap">
                      <Link to={`/projects/${project.id}`}>
                        <Button variant="outline" size="sm" className="h-6 px-2 text-[11px]">
                          Inspect Report
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
