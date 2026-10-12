import { useState, useEffect, useCallback, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { projectsApi, findingsApi, traceabilityApi, API_URL } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SearchInput } from '@/components/ui/input'
import { EmptyState } from '@/components/ui/empty-state'
import { Breadcrumbs } from '@/components/ui/page-header'
import { Skeleton, SkeletonTable } from '@/components/ui/skeleton'
import {
  cn,
  severityColor,
  severityBorderColor,
  statusColor,
  traceStatusColor,
  formatDate,
} from '@/lib/utils'
import {
  Download,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  Link2,
  GitCompare,
  BarChart2,
  Printer,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
} from 'lucide-react'

/* ---------- Data Contracts ---------- */
interface Project {
  id: number
  name: string
  description?: string
  version: number
  status: string
  created_at: string
}

interface Finding {
  id: number
  rule_id: string
  severity: string
  explanation: string
  quoted_text?: string
  artifact_type?: string
  requirement_id?: string
  finding_type?: string
  rewrite_suggestion?: string
  rewrite_passed?: boolean
  rewrite_attempts?: number
}

interface TraceLink {
  id: number
  source_id: string
  source_type: string
  target_id: string
  target_type: string
  status: string
}

interface CompareData {
  resolved_findings?: Finding[]
  new_findings?: Finding[]
  persistent_findings?: Finding[]
}

/* ---------- Sub-components ---------- */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-[#303136] bg-[#17181B] text-[10px] font-mono text-[#A1A1AA] hover:text-[#E7E7E9] hover:border-[#7895B5]/60 transition-none"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-[#68A86C]" />
          <span className="text-[#68A86C]">COPIED</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>COPY</span>
        </>
      )}
    </button>
  )
}

function FindingItem({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div
      className={cn(
        "rounded border border-[#303136] bg-[#1D1E22] overflow-hidden border-l-[3px]",
        severityBorderColor(finding.severity)
      )}
    >
      {/* Header bar */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="p-3 flex items-start gap-2.5 cursor-pointer hover:bg-[#24252A]/40 select-none transition-none"
      >
        <button
          type="button"
          className="mt-0.5 text-[#777981] hover:text-[#E7E7E9]"
          aria-label={expanded ? "Collapse finding" : "Expand finding"}
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span
              className={cn(
                "inline-flex items-center px-1.5 py-0.2 rounded-sm text-[10px] font-mono uppercase font-semibold border",
                severityColor(finding.severity)
              )}
            >
              {finding.severity}
            </span>

            <span className="text-[11px] font-mono text-[#7895B5] bg-[#17181B] border border-[#303136] px-1.5 py-0.2 rounded-sm">
              {finding.rule_id}
            </span>

            {finding.requirement_id && (
              <span className="text-[11px] font-mono text-[#A1A1AA] bg-[#17181B] border border-[#303136] px-1.5 py-0.2 rounded-sm">
                {finding.requirement_id}
              </span>
            )}

            {finding.artifact_type && (
              <span className="text-[10px] font-mono uppercase text-[#777981] border border-[#303136] px-1 py-0.2 rounded-sm">
                {finding.artifact_type}
              </span>
            )}
          </div>

          <p className="text-xs text-[#E7E7E9] leading-relaxed">
            {finding.explanation}
          </p>
        </div>
      </div>

      {/* Expanded Technical Inspection Details */}
      {expanded && (
        <div className="border-t border-[#303136] bg-[#17181B] p-3 space-y-3 text-xs">
          {/* Problematic Quoted Text */}
          {finding.quoted_text && (
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-[#777981] mb-1">
                Problematic Excerpt
              </p>
              <div className="border-l-2 border-[#C04848]/60 pl-2.5 py-1.5 bg-[#141518] text-[#E7E7E9]/90 font-mono text-xs rounded-r">
                "{finding.quoted_text}"
              </div>
            </div>
          )}

          {/* AI Revision Suggestion */}
          {finding.rewrite_suggestion && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-[#777981]">
                    Proposed Formal Revision
                  </p>
                  {finding.rewrite_passed !== undefined && (
                    <span className={cn(
                      "text-[10px] font-mono px-1 py-0.2 rounded-sm border",
                      finding.rewrite_passed
                        ? "text-[#68A86C] border-[#4E8752]/40 bg-[#4E8752]/10"
                        : "text-[#E06C6C] border-[#C04848]/40 bg-[#C04848]/10"
                    )}>
                      {finding.rewrite_passed ? 'VERIFIED PASSED' : 'CHECK FAILED'}
                    </span>
                  )}
                  {finding.rewrite_attempts !== undefined && finding.rewrite_attempts > 0 && (
                    <span className="text-[10px] font-mono text-[#777981]">
                      ({finding.rewrite_attempts} iteration{finding.rewrite_attempts !== 1 ? 's' : ''})
                    </span>
                  )}
                </div>
                <CopyButton text={finding.rewrite_suggestion} />
              </div>

              <div className="p-2.5 rounded border border-[#303136] bg-[#141518] text-xs font-mono text-[#E7E7E9] whitespace-pre-wrap leading-relaxed">
                {finding.rewrite_suggestion}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ---------- Main Component ---------- */
export default function ReportPage() {
  const { id } = useParams()
  const projectId = Number(id)

  const [project, setProject] = useState<Project | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [traceLinks, setTraceLinks] = useState<TraceLink[]>([])
  const [compareData, setCompareData] = useState<CompareData | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'findings' | 'traceability' | 'compare'>('findings')
  const [loading, setLoading] = useState(true)

  // Filters
  const [findingSearch, setFindingSearch] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [traceFilter, setTraceFilter] = useState<string>('all')

  const fetchTraceLinks = useCallback(() => {
    traceabilityApi.getByProject(projectId).then(res => setTraceLinks(res.data)).catch(() => {})
  }, [projectId])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      projectsApi.get(projectId).then(res => {
        setProject(res.data)
        if (res.data.version > 1) {
          projectsApi.compare(projectId, res.data.version - 1).then(cRes => setCompareData(cRes.data)).catch(() => {})
        }
      }),
      findingsApi.getByProject(projectId).then(res => setFindings(res.data)),
      fetchTraceLinks(),
    ]).finally(() => setLoading(false))
  }, [projectId, fetchTraceLinks])

  const updateLinkStatus = async (linkId: number, status: string) => {
    try {
      const token = localStorage.getItem('token')
      await fetch(`${API_URL}/traceability/${linkId}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      fetchTraceLinks()
    } catch (e) {
      console.error(e)
    }
  }

  const downloadTraceability = () => {
    const token = localStorage.getItem('token')
    fetch(`${API_URL}/traceability/project/${projectId}/export`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
      .then(res => res.blob())
      .then(blob => {
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `traceability_${projectId}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      })
  }

  // Filtered findings
  const filteredFindings = useMemo(() => {
    return findings.filter(f => {
      if (severityFilter !== 'all' && f.severity?.toLowerCase() !== severityFilter.toLowerCase()) return false
      if (findingSearch) {
        const q = findingSearch.toLowerCase()
        return (
          f.explanation?.toLowerCase().includes(q) ||
          f.rule_id?.toLowerCase().includes(q) ||
          (f.requirement_id && f.requirement_id.toLowerCase().includes(q)) ||
          (f.quoted_text?.toLowerCase().includes(q) ?? false)
        )
      }
      return true
    })
  }, [findings, severityFilter, findingSearch])

  // Severity counts
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, major: 0, minor: 0, info: 0 }
    findings.forEach(f => {
      const s = f.severity?.toLowerCase()
      if (counts[s] !== undefined) counts[s]++
    })
    return counts
  }, [findings])

  // Filtered trace links
  const filteredTraceLinks = useMemo(() => {
    if (traceFilter === 'all') return traceLinks
    return traceLinks.filter(t => t.status?.toLowerCase() === traceFilter.toLowerCase())
  }, [traceLinks, traceFilter])

  // Trace counts
  const traceStatusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: traceLinks.length, suggested: 0, confirmed: 0, rejected: 0 }
    traceLinks.forEach(t => {
      const s = t.status?.toLowerCase()
      if (counts[s] !== undefined) counts[s]++
    })
    return counts
  }, [traceLinks])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-full" />
        <SkeletonTable rows={8} cols={4} />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Breadcrumb path */}
      <Breadcrumbs
        items={[
          { label: 'Specifications', href: '/projects' },
          { label: project?.name || 'Inspection Report' },
        ]}
      />

      {/* Inspection Header */}
      {project && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-[#303136]">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold text-[#E7E7E9] tracking-tight">
                {project.name}
              </h1>
              <span className="font-mono text-xs px-1.5 py-0.2 rounded border border-[#303136] bg-[#17181B] text-[#A1A1AA]">
                v{project.version}
              </span>
              <span className={cn(
                "inline-flex items-center px-1.5 py-0.2 rounded-sm text-[10px] font-mono border uppercase",
                statusColor(project.status)
              )}>
                {project.status}
              </span>
            </div>
            <p className="text-[11px] font-mono text-[#777981] mt-0.5">
              ID: {project.id} • Evaluated: {formatDate(project.created_at)}
            </p>
          </div>

          <div className="flex items-center gap-1.5 print:hidden">
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer className="mr-1.5 h-3.5 w-3.5" />
              Print
            </Button>
            <Button variant="outline" size="sm" onClick={downloadTraceability}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Traceability CSV
            </Button>
          </div>
        </div>
      )}

      {/* Tab Navigation Strip */}
      <div className="flex items-center border-b border-[#303136] text-xs font-mono print:hidden">
        {[
          { id: 'findings', label: 'Findings', count: findings.length },
          { id: 'traceability', label: 'Traceability Matrix', count: traceLinks.length },
          { id: 'overview', label: 'Inspection Telemetry' },
          { id: 'compare', label: 'Version Diff' },
        ].map(tab => {
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                "px-3 py-2 border-b-2 transition-none flex items-center gap-1.5",
                active
                  ? "border-b-[#7895B5] text-[#E7E7E9] font-medium bg-[#1D1E22]/40"
                  : "border-b-transparent text-[#777981] hover:text-[#A1A1AA] hover:bg-[#1D1E22]/20"
              )}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="text-[10px] px-1 py-0.2 rounded bg-[#17181B] border border-[#303136] text-[#A1A1AA]">
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* ===== FINDINGS TAB ===== */}
      {activeTab === 'findings' && (
        <div className="space-y-3">
          {/* Findings Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
            <SearchInput
              placeholder="Search findings by rule ID, requirement, or explanation..."
              value={findingSearch}
              onChange={e => setFindingSearch(e.target.value)}
              className="max-w-md h-8 text-xs"
            />

            <div className="flex items-center gap-1 border border-[#303136] rounded p-0.5 bg-[#17181B] text-xs font-mono">
              {(['all', 'critical', 'major', 'minor', 'info'] as const).map(sev => {
                const count = sev === 'all' ? findings.length : (severityCounts[sev] || 0)
                const active = severityFilter === sev
                return (
                  <button
                    key={sev}
                    onClick={() => setSeverityFilter(sev)}
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] uppercase transition-none",
                      active
                        ? "bg-[#1D1E22] text-[#E7E7E9] font-medium border border-[#303136]"
                        : "text-[#777981] hover:text-[#A1A1AA]"
                    )}
                  >
                    {sev}
                    <span className="ml-1 text-[9px] text-[#777981]">({count})</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Finding Cards List */}
          {filteredFindings.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title={findings.length === 0 ? 'No defects recorded' : 'No findings match query'}
              description={findings.length === 0
                ? 'All requirement verification rules evaluated successfully without violations.'
                : 'Clear or modify your search and severity filters to view other findings.'
              }
              action={findings.length > 0 ? {
                label: "Clear Filters",
                onClick: () => {
                  setFindingSearch('')
                  setSeverityFilter('all')
                }
              } : undefined}
            />
          ) : (
            <div className="space-y-2">
              {filteredFindings.map(f => (
                <FindingItem key={f.id} finding={f} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* ===== TRACEABILITY TAB ===== */}
      {activeTab === 'traceability' && (
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-1 border border-[#303136] rounded p-0.5 bg-[#17181B] text-xs font-mono">
              {(['all', 'suggested', 'confirmed', 'rejected'] as const).map(status => {
                const active = traceFilter === status
                return (
                  <button
                    key={status}
                    onClick={() => setTraceFilter(status)}
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] uppercase transition-none",
                      active
                        ? "bg-[#1D1E22] text-[#E7E7E9] font-medium border border-[#303136]"
                        : "text-[#777981] hover:text-[#A1A1AA]"
                    )}
                  >
                    {status}
                    <span className="ml-1 text-[9px] text-[#777981]">
                      ({traceStatusCounts[status] ?? 0})
                    </span>
                  </button>
                )
              })}
            </div>

            <Button variant="outline" size="sm" onClick={downloadTraceability}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Download Matrix (.csv)
            </Button>
          </div>

          <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden">
            <div className="overflow-x-auto scrollbar-technical">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#303136] bg-[#17181B] text-[10px] font-mono uppercase tracking-wider text-[#777981]">
                    <th className="py-2.5 px-3.5 font-medium">Source Requirement</th>
                    <th className="py-2.5 px-3 font-medium text-center">Status</th>
                    <th className="py-2.5 px-3 font-medium">Target Architecture Element</th>
                    <th className="py-2.5 px-3.5 text-right font-medium print:hidden">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#303136]/50">
                  {filteredTraceLinks.length === 0 ? (
                    <tr>
                      <td colSpan={4}>
                        <EmptyState
                          icon={Link2}
                          title={traceLinks.length === 0 ? 'No traceability traces mapped' : 'No trace links match filter'}
                          description={traceLinks.length === 0
                            ? 'UML model diagrams (.puml) must be uploaded to generate automated architecture mappings.'
                            : 'Adjust the status filter to inspect other trace links.'
                          }
                          className="m-4 border-0"
                        />
                      </td>
                    </tr>
                  ) : (
                    filteredTraceLinks.map(t => (
                      <tr key={t.id} className="hover:bg-[#24252A]/40 transition-none">
                        <td className="py-2.5 px-3.5 font-mono">
                          <span className="font-semibold text-[#E7E7E9]">{t.source_id}</span>
                          <span className="text-[10px] text-[#777981] ml-1.5">[{t.source_type}]</span>
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <span
                            className={cn(
                              "inline-flex items-center px-1.5 py-0.2 rounded-sm text-[10px] font-mono border uppercase",
                              traceStatusColor(t.status)
                            )}
                          >
                            {t.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          <span className="font-semibold text-[#E7E7E9]">{t.target_id}</span>
                          <span className="text-[10px] text-[#777981] ml-1.5">[{t.target_type}]</span>
                        </td>
                        <td className="py-2.5 px-3.5 text-right whitespace-nowrap print:hidden">
                          {t.status === 'suggested' ? (
                            <div className="flex items-center justify-end gap-1 font-mono">
                              <button
                                onClick={() => updateLinkStatus(t.id, 'confirmed')}
                                className="px-2 py-0.5 rounded border border-[#4E8752]/40 bg-[#4E8752]/10 text-[#68A86C] text-[10px] hover:bg-[#4E8752]/20"
                              >
                                Confirm
                              </button>
                              <button
                                onClick={() => updateLinkStatus(t.id, 'rejected')}
                                className="px-2 py-0.5 rounded border border-[#C04848]/40 bg-[#C04848]/10 text-[#E06C6C] text-[10px] hover:bg-[#C04848]/20"
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-[10px] font-mono text-[#777981]">
                              REVIEWED
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===== TELEMETRY & OVERVIEW TAB ===== */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="rounded border border-[#303136] bg-[#17181B] divide-y sm:divide-y-0 sm:divide-x divide-[#303136] grid grid-cols-2 sm:grid-cols-4">
            <div className="p-3.5">
              <p className="text-[10px] font-mono uppercase text-[#777981]">Evaluation Status</p>
              <p className="text-base font-mono font-semibold text-[#E7E7E9] mt-0.5 capitalize">
                {project?.status}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-[10px] font-mono uppercase text-[#777981]">Total Findings</p>
              <p className="text-base font-mono font-semibold text-[#E7E7E9] mt-0.5">
                {findings.length}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-[10px] font-mono uppercase text-[#777981]">Architecture Traces</p>
              <p className="text-base font-mono font-semibold text-[#E7E7E9] mt-0.5">
                {traceLinks.length}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-[10px] font-mono uppercase text-[#777981]">Specification Revision</p>
              <p className="text-base font-mono font-semibold text-[#E7E7E9] mt-0.5">
                v{project?.version || 1}
              </p>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden">
            <div className="p-3 border-b border-[#303136] bg-[#17181B]">
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
                Defect Severity Breakdown
              </h3>
            </div>
            <div className="divide-y divide-[#303136] text-xs font-mono">
              {(['critical', 'major', 'minor', 'info'] as const).map(sev => (
                <div key={sev} className="p-3 flex items-center justify-between hover:bg-[#24252A]/40">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "w-2 h-2 rounded-full",
                      sev === 'critical' ? 'bg-[#C04848]' : sev === 'major' ? 'bg-[#B8863A]' : sev === 'minor' ? 'bg-[#A89048]' : 'bg-[#7895B5]'
                    )} />
                    <span className="uppercase text-[#E7E7E9]">{sev}</span>
                  </div>
                  <span className="font-semibold text-[#E7E7E9]">
                    {severityCounts[sev] || 0}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ===== VERSION DIFF TAB ===== */}
      {activeTab === 'compare' && (
        <div className="space-y-4">
          {!compareData ? (
            <EmptyState
              icon={GitCompare}
              title="No previous version comparison"
              description="Upload a subsequent revision of this specification with identical project name to calculate regression and resolution diffs."
              className="border rounded bg-[#1D1E22]"
            />
          ) : (
            <div className="space-y-4">
              {/* Resolved */}
              <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden border-l-[3px] border-l-[#4E8752]">
                <div className="p-3 border-b border-[#303136] bg-[#17181B] flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-[#68A86C]">
                    Resolved Defects ({compareData.resolved_findings?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-[#777981]">
                    Fixed compared to v{(project?.version || 2) - 1}
                  </span>
                </div>
                <div className="p-3 text-xs">
                  {!compareData.resolved_findings?.length ? (
                    <p className="text-[#777981] font-mono">Zero previously reported defects were resolved.</p>
                  ) : (
                    <div className="divide-y divide-[#303136]/50">
                      {compareData.resolved_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-[10px] text-[#7895B5] bg-[#17181B] border border-[#303136] px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-[#E7E7E9]">{f.explanation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* New Defects */}
              <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden border-l-[3px] border-l-[#C04848]">
                <div className="p-3 border-b border-[#303136] bg-[#17181B] flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-[#E06C6C]">
                    Newly Introduced Defects ({compareData.new_findings?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-[#777981]">
                    Regressions introduced in v{project?.version}
                  </span>
                </div>
                <div className="p-3 text-xs">
                  {!compareData.new_findings?.length ? (
                    <p className="text-[#777981] font-mono">No new defect regressions introduced.</p>
                  ) : (
                    <div className="divide-y divide-[#303136]/50">
                      {compareData.new_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-[10px] text-[#E06C6C] bg-[#17181B] border border-[#C04848]/40 px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-[#E7E7E9]">{f.explanation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Persistent Defects */}
              <div className="rounded border border-[#303136] bg-[#1D1E22] overflow-hidden border-l-[3px] border-l-[#B8863A]">
                <div className="p-3 border-b border-[#303136] bg-[#17181B] flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-[#D49E4B]">
                    Persistent Unresolved Defects ({compareData.persistent_findings?.length || 0})
                  </span>
                  <span className="text-[10px] font-mono text-[#777981]">
                    Carried over from prior revision
                  </span>
                </div>
                <div className="p-3 text-xs">
                  <p className="text-[#777981] font-mono mb-2">
                    {compareData.persistent_findings?.length
                      ? `${compareData.persistent_findings.length} defect(s) remain unresolved across revisions.`
                      : 'All prior revision defects addressed.'}
                  </p>
                  {compareData.persistent_findings && compareData.persistent_findings.length > 0 && (
                    <div className="divide-y divide-[#303136]/50">
                      {compareData.persistent_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-[10px] text-[#A1A1AA] bg-[#17181B] border border-[#303136] px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-[#E7E7E9]">{f.explanation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
