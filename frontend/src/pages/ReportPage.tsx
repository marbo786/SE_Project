import { TraceMatrix } from '@/components/report/TraceMatrix'
import { ScoreSummary } from '@/components/report/ScoreSummary'
import { ImpactPaths } from '@/components/report/ImpactPaths'
import { SourcePanel, type SourceRequirement } from '@/components/report/SourcePanel'
import { FindingDecision } from '@/components/report/FindingDecision'
import { PrintReport } from '@/components/report/PrintReport'
import { RevisionDiff } from '@/components/report/RevisionDiff'
import { ProjectWorkspace } from '@/components/report/ProjectWorkspace'
import { ManualTrace } from '@/components/report/ManualTrace'
import { useState, useMemo, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useSearchParams, useNavigate } from 'react-router-dom'
import { projectsApi, historyApi, apiError, RunSummary } from '@/lib/api'
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

import type { Project, Finding, TraceLink, CompareData, SuggestionDecision } from '@/components/report/types'
import { FindingItem, SuggestionReview } from '@/components/report/FindingItem'

/* ---------- Main Component ---------- */
export default function ReportPage() {
  const [actionError, setActionError] = useState('')
  const { id } = useParams()
  const projectId = Number(id)
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const selectedRun = params.get('run')

  const queryClient = useQueryClient()
  const report = useQuery({
    queryKey: ['project-report', projectId, selectedRun],
    enabled: Number.isInteger(projectId) && projectId > 0,
    queryFn: async ({ signal }) => {
      const [response, history] = await Promise.all([projectsApi.get(projectId, signal), historyApi.runs(projectId, signal)])
      const live = response.data as Project
      const runId = selectedRun || live.published_run_id || live.latest_run_id
      const run = runId ? (await historyApi.run(runId, signal)).data : null
      if (run && run.project_id !== projectId) throw new Error('Run does not belong to this project')
      const snapshot = run?.has_report ? (await historyApi.report(run.id, signal)).data : null
      const revision = run ? (await historyApi.revision(projectId, run.revision_id, signal)).data : null
      const reviews = (snapshot?.reviews || []) as { id: number; trace_id?: number; finding_id?: number; status: string }[]
      const links = ((snapshot?.trace_links || []) as TraceLink[]).map(link => ({ ...link, status: reviews.find(review => review.trace_id === link.id)?.status || link.status }))
      return { live, snapshot, revision, runs: history.data.items, run, reviews,
        suggestions: (snapshot?.suggestion_decisions || []) as SuggestionDecision[],
        aiUsage: snapshot?.ai_usage as { provider_calls: number; cache_hits: number; reported_tokens: number; unknown_usage_calls: number; reserved_unknown_tokens: number; estimated_cost_microusd: number; reserved_unknown_cost_microusd: number; unpriced_calls: number } | undefined,
        project: { ...live, version: revision?.number || live.version, quality_score: snapshot?.score,
          analysis_mode: revision?.analysis_mode || live.analysis_mode,
          status: run ? ({ completed: 'done', failed: 'error', queued: 'analyzing', running: 'analyzing', partial: 'partial', cancelled: 'cancelled' }[run.status] || run.status) : live.status,
          analysis_error: run?.error_message || undefined } as Project,
        findings: (snapshot?.findings || []) as Finding[], links }
    },
    refetchInterval: query => query.state.data?.live.status === 'analyzing' || ['queued', 'running'].includes(query.state.data?.run?.status || '') ? 2000 * Math.min(8, 2 ** query.state.fetchFailureCount) : false,
    refetchIntervalInBackground: false,
  })
  const project = report.data?.project ?? null
  const findings = report.data?.findings ?? []
  const sources = Object.values(report.data?.snapshot?.extractions || {}).flatMap((extraction: any) => extraction.requirements || []) as SourceRequirement[]
  const warnings = (report.data?.snapshot?.warnings || []) as string[]
  const selectedFinding = findings.find(f => String(f.id) === params.get('finding'))
  const reviewFilter = params.get('review') || 'all'
  const [reviewBusy, setReviewBusy] = useState(false)
  const traceLinks = report.data?.links ?? []
  const loading = report.isPending
  const updateParams = (values: Record<string, string>) => setParams(previous => { const next = new URLSearchParams(previous); Object.entries(values).forEach(([key, value]) => value ? next.set(key, value) : next.delete(key)); return next }, { replace: true })
  const activeTab = params.get('tab') || 'overview'
  const setActiveTab = (tab: string) => updateParams({ tab })
  const previousRun = params.get('compare') || ''
  const setPreviousRun = (value: string) => updateParams({ compare: value })
  const comparison = useQuery({
    queryKey: ['project-comparison', projectId, report.data?.run?.id, previousRun],
    enabled: !!report.data?.run && !!previousRun && activeTab === 'compare',
    queryFn: async () => (await historyApi.compare(report.data!.run!.id, previousRun)).data as CompareData,
  })
  const compareData = comparison.data
  const rerun = useMutation({
    mutationFn: async () => {
      const live = report.data!.live
      const revision = (await historyApi.revision(projectId, live.current_revision_id)).data
      if (revision.state === 'draft') { navigate(`/projects/${projectId}/revisions/${revision.id}`); return null }
      return historyApi.start(projectId, revision, crypto.randomUUID())
    },
    onSuccess: response => { setActionError(''); if (response) setParams({ run: response.data.id }); void queryClient.invalidateQueries({ queryKey: ['project-report', projectId] }) },
    onError: error => setActionError(apiError(error, 'Analysis could not start.')),
  })

  // Filters
  const findingSearch = params.get('q') || ''
  const setFindingSearch = (value: string) => updateParams({ q: value })
  const severityFilter = params.get('severity') || 'all'
  const setSeverityFilter = (value: string) => updateParams({ severity: value })
  const traceFilter = params.get('trace') || 'all'
  const setTraceFilter = (value: string) => updateParams({ trace: value })

  const updateLinkStatus = async (linkId: number, status: 'suggested' | 'confirmed' | 'rejected') => {
    setReviewBusy(true); setActionError('')
    try {
      if (!report.data?.run) return
      await historyApi.decision(report.data.run.id, { target_type: 'trace', target_id: linkId, status,
        expected_decision_id: report.data.reviews.find(review => review.trace_id === linkId)?.id || 0 })
      await queryClient.invalidateQueries({ queryKey: ['project-report', projectId] })
    } catch (e) {
      setActionError(apiError(e))
    } finally { setReviewBusy(false) }
  }

  const downloadTraceability = async () => {
    setActionError('')
    try {
      if (!report.data?.run?.has_report) return
      const response = await historyApi.exportTrace(report.data.run.id)
      const url = window.URL.createObjectURL(response.data)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `traceability_${projectId}.csv`
      anchor.click()
      window.URL.revokeObjectURL(url)
    } catch (error) { setActionError(apiError(error, 'Export failed. Please try again.')) }
  }

  // Filtered findings
  const filteredFindings = useMemo(() => {
    return findings.filter(f => {
      if (reviewFilter !== 'all' && (report.data?.reviews.find(review => review.finding_id === f.id)?.status || 'needs_review') !== reviewFilter) return false
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
    }).sort((a, b) => ['critical', 'major', 'minor', 'info'].indexOf(a.severity) - ['critical', 'major', 'minor', 'info'].indexOf(b.severity))
  }, [findings, severityFilter, findingSearch, reviewFilter, report.data?.reviews])

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
    if (traceFilter === 'stale') return traceLinks.filter(t => t.is_stale)
    return traceLinks.filter(t => t.status?.toLowerCase() === traceFilter.toLowerCase())
  }, [traceLinks, traceFilter])

  // Trace counts
  const traceStatusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: traceLinks.length, suggested: 0, confirmed: 0, rejected: 0, stale: traceLinks.filter(t => t.is_stale).length }
    traceLinks.forEach(t => {
      const s = t.status?.toLowerCase()
      if (counts[s] !== undefined) counts[s]++
    })
    return counts
  }, [traceLinks])

  if (!Number.isInteger(projectId) || projectId < 1) return <p role="alert">This project link is invalid.</p>
  if (report.isError && !project) return <div role="alert" className="space-y-3"><p>{apiError(report.error, 'The report could not be loaded.')}</p><Button onClick={() => report.refetch()}>Try again</Button></div>
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
    <>
    {project && <PrintReport project={project} run={report.data?.run} findings={findings} links={traceLinks} reviews={report.data?.reviews || []} warnings={warnings} />}
    <div className="space-y-4 report-screen print:hidden">
      {project && <ProjectWorkspace key={project.id} id={projectId} name={project.name} archived={!!report.data?.live.archived_at} saved={() => queryClient.invalidateQueries({ queryKey: ['project-report', projectId] })} />}
      <section aria-label="Analysis history" className="border border-border rounded p-4 flex flex-wrap gap-4 items-end print:hidden">
        <label className="flex-1 min-w-0 text-sm space-y-2"><span>Analysis history</span><select className="block w-full rounded border border-border bg-secondary p-2" value={selectedRun || ''} onChange={event => { updateParams({ run: event.target.value, compare: '', finding: '' }) }}>
          <option value="">Published report</option>{report.data?.runs.map((run: RunSummary) => <option key={run.id} value={run.id}>{formatDate(run.created_at)} — {run.status} ({run.id.slice(0, 8)})</option>)}
        </select></label>
        <Button variant="outline" disabled={report.data?.live.status === 'analyzing'} onClick={async () => { try { const draft = await historyApi.draft(projectId, report.data?.run?.revision_id); navigate(`/projects/${projectId}/revisions/${draft.data.id}`) } catch (error) { setActionError(apiError(error)) } }}>Edit a new draft</Button>
      </section>
      {report.data?.live.latest_run_id && report.data.live.latest_run_id !== report.data.run?.id && <p role="status" className="p-3 border border-amber-300 rounded">Showing a preserved report. A newer analysis attempt is available in the history menu. <button className="underline" onClick={() => setParams({ run: report.data!.live.latest_run_id! })}>View latest attempt</button></p>}
      {report.data?.run && ['queued', 'running'].includes(report.data.run.status) && <div role="status" className="p-4 border rounded space-y-2">
        <p>{report.data.run.status === 'queued' ? 'Queued for analysis' : `Analysis stage: ${report.data.run.stage.replace(/_/g, ' ')}`} · Attempt {report.data.run.attempt_count}</p><p>{Object.entries(report.data.run.counts || {}).map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`).join(' · ')}</p>
        {report.data.run.cancel_requested ? <p>Cancellation requested. An external AI request already in progress may finish; its result will not be published.</p> : <Button variant="outline" onClick={async () => { try { await historyApi.cancel(report.data!.run!.id); await queryClient.invalidateQueries({ queryKey: ['project-report', projectId] }) } catch (error) { setActionError(apiError(error)) } }}>Cancel analysis</Button>}
      </div>}
      {report.data?.run?.status === 'cancelled' && <p role="status" className="p-4 border rounded">This analysis was cancelled. Earlier reports remain available in history.</p>}
      {actionError && <p role="alert" className="p-3 border border-red-400 text-red-300">{actionError}</p>}
      {report.isError && <p role="alert">Unable to refresh. Showing the last loaded report. <button onClick={() => report.refetch()}>Retry</button></p>}
      {comparison.isError && activeTab === 'compare' && <p role="alert">{apiError(comparison.error, 'Comparison is unavailable.')} <button onClick={() => comparison.refetch()}>Retry</button></p>}
      {project?.status === 'analyzing' && <p role="status" aria-live="polite" className="p-4 border border-blue-400 rounded">Analysis is running. This report updates automatically. Any results below are from the previous completed analysis.</p>}
      {report.data?.live.status === 'pending' && <p role="status" className="p-4 border rounded">A draft is ready to edit. <Link className="underline" to={`/projects/${projectId}/revisions/${report.data.live.current_revision_id}`}>Continue draft</Link></p>}
      {project?.analysis_mode === 'ai' && report.data?.aiUsage && <section aria-label="AI usage" className="p-4 border border-border rounded text-sm space-y-1">
        <p>AI usage: {report.data.aiUsage.provider_calls} provider calls, {report.data.aiUsage.cache_hits} cached responses, {report.data.aiUsage.reported_tokens} provider-reported tokens.</p>
        {report.data.aiUsage.unknown_usage_calls > 0 && <p>Usage is unknown for {report.data.aiUsage.unknown_usage_calls} calls. Their {report.data.aiUsage.reserved_unknown_tokens} reserved tokens remain charged against this run's budget; this is not measured usage or a cost estimate.</p>}
      </section>}
      {report.data?.aiUsage && project?.analysis_mode === 'ai' && <p className="text-sm">Configured-price estimate: ${((report.data.aiUsage.estimated_cost_microusd || 0) / 1000000).toFixed(6)}; unknown-usage reservation: ${((report.data.aiUsage.reserved_unknown_cost_microusd || 0) / 1000000).toFixed(6)}. {report.data.aiUsage.unpriced_calls || 0} calls have no price. These are not provider invoices.</p>}
      {project?.analysis_mode === 'ai' && project.quality_score?.details?.ai_coverage && <section aria-label="AI review coverage" className="border border-border rounded p-4 text-sm space-y-2">
        {Object.entries(project.quality_score.details.ai_coverage).map(([name, coverage]) => <p key={name}>{name}: {coverage.reviewed} / {coverage.total} reviewed ({coverage.complete ? 'complete' : 'partial'}). {coverage.note}</p>)}
      </section>}
      {project?.status === 'partial' && <p role="status" className="p-4 border border-amber-400 rounded">Some inputs or requested checks could not be fully evaluated. Review the warnings below; no final grade is assigned.</p>}
      {project?.analysis_error && <p role="alert" className="p-4 border border-red-400 rounded">{project.analysis_error}</p>}
      {project && <ScoreSummary project={project} />}
      {!!report.data?.snapshot?.review_carry?.stale_decisions && <p role="status" className="border rounded p-4">{report.data.snapshot.review_carry.stale_decisions} earlier review decisions were not carried forward because inputs or analysis versions changed. Review the current evidence again.</p>}
      {warnings.length > 0 && <section aria-label="Analysis warnings" className="border rounded p-4"><h2 className="font-semibold">Analysis warnings</h2><ul>{warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></section>}
      {/* Breadcrumb path */}
      <Breadcrumbs
        items={[
          { label: 'Specifications', href: '/projects' },
          { label: project?.name || 'Inspection Report' },
        ]}
      />

      {/* Inspection Header */}
      {project && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-border">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-base font-semibold text-foreground tracking-tight">
                {project.name}
              </h1>
              <span className="font-mono text-xs px-1.5 py-0.2 rounded border border-border bg-secondary text-muted-foreground">
                v{project.version}
              </span>
              <span className={cn(
                "inline-flex items-center px-1.5 py-0.2 rounded-sm text-xs font-mono border uppercase",
                statusColor(project.status)
              )}>
                {project.status}
              </span>
            </div>
            <p className="text-xs font-mono text-muted-foreground mt-0.5">
              ID: {project.id} • {project.quality_score ? 'Evaluated' : 'Created'}: {formatDate(project.quality_score?.computed_at || project.created_at)}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 print:hidden">
            <Button size="sm" disabled={report.data?.live.status === 'analyzing' || rerun.isPending} onClick={() => rerun.mutate()}>
              {project.status === 'analyzing' ? 'Analyzing…' : rerun.isPending ? 'Starting…' : project.status === 'pending' ? 'Analyze' : 'Run again'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer className="mr-1.5 h-3.5 w-3.5" />
              Print
            </Button>
            <Button variant="outline" size="sm" disabled={!report.data?.run?.has_report} onClick={downloadTraceability}>
              <Download className="mr-1.5 h-3.5 w-3.5" />
              Traceability CSV
            </Button>
          </div>
        </div>
      )}

      {/* Tab Navigation Strip */}
      <div className="flex flex-wrap items-center border-b border-border text-sm print:hidden">
        {[
          { id: 'findings', label: 'Findings', count: findings.length },
          { id: 'traceability', label: 'Traceability Matrix', count: traceLinks.length },
          { id: 'overview', label: 'Summary' },
          { id: 'compare', label: 'Compare revisions' },
        ].map(tab => {
          const active = activeTab === tab.id
          return (
            <button
              key={tab.id}
              aria-pressed={active}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-3 py-2 border-b-2 transition-none flex items-center gap-1.5",
                active
                  ? "border-b-primary text-foreground font-medium bg-card/40"
                  : "border-b-transparent text-muted-foreground hover:text-muted-foreground hover:bg-card/20"
              )}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="text-xs px-1 py-0.2 rounded bg-secondary border border-border text-muted-foreground">
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
              aria-label="Search findings"
              placeholder="Search findings by rule ID, requirement, or explanation..."
              value={findingSearch}
              onChange={e => setFindingSearch(e.target.value)}
              className="max-w-md h-8 text-xs"
            />

            <div className="flex flex-wrap items-center gap-1 border border-border rounded p-0.5 bg-secondary text-xs font-mono">
              {(['all', 'critical', 'major', 'minor', 'info'] as const).map(sev => {
                const count = sev === 'all' ? findings.length : (severityCounts[sev] || 0)
                const active = severityFilter === sev
                return (
                  <button
                    key={sev}
                    aria-pressed={active}
                    onClick={() => setSeverityFilter(sev)}
                    className={cn(
                      "px-2 py-0.5 rounded text-xs uppercase transition-none",
                      active
                        ? "bg-card text-foreground font-medium border border-border"
                        : "text-muted-foreground hover:text-muted-foreground"
                    )}
                  >
                    {sev}
                    <span className="ml-1 text-xs text-muted-foreground">({count})</span>
                  </button>
                )
              })}
            </div>
          </div>

          <label className="block">Review state<select className="block sm:inline-block sm:ml-3 max-w-full border rounded p-2 bg-secondary" value={reviewFilter} onChange={e => updateParams({ review: e.target.value })}><option value="all">All reviews</option><option value="needs_review">Needs review</option><option value="accepted">Accepted findings</option><option value="dismissed">Dismissed findings</option></select></label>
          {selectedFinding && <SourcePanel finding={selectedFinding} requirements={sources} projectId={projectId} />}
          {/* Finding Cards List */}
          {filteredFindings.length === 0 ? (
            <EmptyState
              icon={ShieldAlert}
              title={findings.length === 0 ? (project?.status === 'done' ? 'No findings in the evaluated scope' : 'Results are not available yet') : 'No findings match query'}
              description={findings.length === 0
                ? 'An empty result is not proof of correctness. Check the analysis status and evaluated scope above.'
                : 'Clear or modify your search and severity filters to view other findings.'
              }
              action={findings.length > 0 ? {
                label: "Clear Filters",
                onClick: () => {
                  updateParams({ q: '', severity: '', review: '' })
                }
              } : undefined}
            />
          ) : (
            <div className="space-y-2">
              {filteredFindings.map(f => (
                <article key={`${report.data?.run?.id}:${f.id}`} id={`finding-${f.id}`} className="space-y-2">
                  <button className="text-primary underline" onClick={() => updateParams({ finding: String(f.id) })}>View source for {f.requirement_id || f.rule_id}</button>
                  <FindingItem finding={f} review={report.data?.run && <>
                    <FindingDecision runId={report.data.run.id} findingId={f.id} decision={report.data.reviews.find(item => item.finding_id === f.id)} saved={() => queryClient.invalidateQueries({ queryKey: ['project-report', projectId] })} />
                    {f.rewrite_suggestion && <SuggestionReview finding={f} projectId={projectId} run={report.data.run} decision={report.data.suggestions.find(item => item.finding_id === f.id)} saved={() => queryClient.invalidateQueries({ queryKey: ['project-report', projectId] })} />}
                  </>} />
                </article>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ===== TRACEABILITY TAB ===== */}
      {activeTab === 'traceability' && (
        <div className="space-y-3">
          {report.data?.run?.has_report && <ManualTrace runId={report.data.run.id} saved={() => queryClient.invalidateQueries({ queryKey: ['project-report', projectId] })} />}
          <p className="text-muted-foreground">Confirm evidence-backed links or reject incorrect mappings. Similarity is not a probability; decisions do not rewrite the published score.</p>
          <Button variant="outline" disabled={reviewBusy || !filteredTraceLinks.some(t => t.status === 'suggested' && !t.is_stale)} onClick={async () => {
            setReviewBusy(true); setActionError('')
            try { for (const link of filteredTraceLinks.filter(t => t.status === 'suggested' && !t.is_stale)) await historyApi.decision(report.data!.run!.id, { target_type: 'trace', target_id: link.id, status: 'confirmed', expected_decision_id: report.data!.reviews.find(r => r.trace_id === link.id)?.id || 0 }) }
            catch (error) { setActionError(apiError(error, 'Bulk review stopped. Saved decisions remain; refresh before retrying.')) }
            finally { await queryClient.invalidateQueries({ queryKey: ['project-report', projectId] }); setReviewBusy(false) }
          }}>Confirm visible suggested links</Button>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1 border border-border rounded p-0.5 bg-secondary text-xs font-mono">
              {(['all', 'suggested', 'confirmed', 'rejected', 'stale'] as const).map(status => {
                const active = traceFilter === status
                return (
                  <button
                    key={status}
                    aria-pressed={active}
                    onClick={() => setTraceFilter(status)}
                    className={cn(
                      "px-2 py-0.5 rounded text-xs uppercase transition-none",
                      active
                        ? "bg-card text-foreground font-medium border border-border"
                        : "text-muted-foreground hover:text-muted-foreground"
                    )}
                  >
                    {status}
                    <span className="ml-1 text-xs text-muted-foreground">
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

          <TraceMatrix filteredTraceLinks={filteredTraceLinks} traceLinks={traceLinks} reviewBusy={reviewBusy} updateLinkStatus={updateLinkStatus} />
        </div>
      )}

      {/* ===== TELEMETRY & OVERVIEW TAB ===== */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          <div className="rounded border border-border bg-secondary divide-y sm:divide-y-0 sm:divide-x divide-border grid grid-cols-2 sm:grid-cols-4">
            <div className="p-3.5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Evaluation Status</p>
              <p className="text-base font-mono font-semibold text-foreground mt-0.5 capitalize">
                {project?.status}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Total Findings</p>
              <p className="text-base font-mono font-semibold text-foreground mt-0.5">
                {findings.length}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Architecture Traces</p>
              <p className="text-base font-mono font-semibold text-foreground mt-0.5">
                {traceLinks.length}
              </p>
            </div>
            <div className="p-3.5">
              <p className="text-xs font-mono uppercase text-muted-foreground">Specification Revision</p>
              <p className="text-base font-mono font-semibold text-foreground mt-0.5">
                v{project?.version || 1}
              </p>
            </div>
          </div>

          {/* Breakdown Table */}
          <div className="rounded border border-border bg-card overflow-hidden">
            <div className="p-3 border-b border-border bg-secondary">
              <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
                Defect Severity Breakdown
              </h3>
            </div>
            <div className="divide-y divide-border text-xs font-mono">
              {(['critical', 'major', 'minor', 'info'] as const).map(sev => (
                <div key={sev} className="p-3 flex items-center justify-between hover:bg-accent/40">
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "w-2 h-2 rounded-full",
                      sev === 'critical' ? 'bg-danger' : sev === 'major' ? 'bg-warning' : sev === 'minor' ? 'bg-warning' : 'bg-primary'
                    )} />
                    <span className="uppercase text-foreground">{sev}</span>
                  </div>
                  <span className="font-semibold text-foreground">
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
          <label className="block text-sm space-y-2"><span>Compare the selected report with</span><select className="block rounded border border-border bg-secondary p-2 w-full" value={previousRun} onChange={event => setPreviousRun(event.target.value)}><option value="">Choose an earlier report</option>{report.data?.runs.filter(run => run.has_report && run.id !== report.data?.run?.id).map(run => <option key={run.id} value={run.id}>{formatDate(run.created_at)} — {run.status} ({run.id.slice(0, 8)})</option>)}</select></label>
          {compareData?.comparability_note && <p className="p-3 border border-amber-300 rounded">{compareData.comparability_note}</p>}
          {compareData?.requirements && <p className="text-sm">Requirements: {compareData.requirements.added.length} added, {compareData.requirements.changed.length} changed, {compareData.requirements.deleted.length} removed.</p>}
          {compareData?.requirements && <><RevisionDiff requirements={compareData.requirements as any} /><ImpactPaths links={traceLinks} changedIds={(compareData.requirements.changed as { after: SourceRequirement }[]).map(item => item.after.internal_id)} /></>}
          {comparison.isFetching ? <p role="status">Loading comparison…</p> : comparison.isError ? null : !compareData ? (
            <EmptyState
              icon={GitCompare}
              title="No previous version comparison"
              description="Create a draft in this project, make your corrections, and analyze it. Both reports remain available for comparison."
              className="border rounded bg-card"
            />
          ) : (
            <div className="space-y-4">
              {/* Resolved */}
              <div className="rounded border border-border bg-card overflow-hidden border-l-[3px] border-l-success">
                <div className="p-3 border-b border-border bg-secondary flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-success">
                    Resolved Defects ({compareData.resolved_findings?.length || 0})
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    Absent from the selected report
                  </span>
                </div>
                <div className="p-3 text-xs">
                  {!compareData.resolved_findings?.length ? (
                    <p className="text-muted-foreground font-mono">Zero previously reported defects were resolved.</p>
                  ) : (
                    <div className="divide-y divide-border/50">
                      {compareData.resolved_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-xs text-primary bg-secondary border border-border px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-foreground">{f.explanation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* New Defects */}
              <div className="rounded border border-border bg-card overflow-hidden border-l-[3px] border-l-danger">
                <div className="p-3 border-b border-border bg-secondary flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-danger">
                    Newly Introduced Defects ({compareData.new_findings?.length || 0})
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    Present in the selected report
                  </span>
                </div>
                <div className="p-3 text-xs">
                  {!compareData.new_findings?.length ? (
                    <p className="text-muted-foreground font-mono">No new defect regressions introduced.</p>
                  ) : (
                    <div className="divide-y divide-border/50">
                      {compareData.new_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-xs text-danger bg-secondary border border-danger/40 px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-foreground">{f.explanation}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Persistent Defects */}
              <div className="rounded border border-border bg-card overflow-hidden border-l-[3px] border-l-warning">
                <div className="p-3 border-b border-border bg-secondary flex items-center justify-between">
                  <span className="text-xs font-mono font-semibold uppercase text-warning">
                    Persistent Unresolved Defects ({compareData.persistent_findings?.length || 0})
                  </span>
                  <span className="text-xs font-mono text-muted-foreground">
                    Carried over from prior revision
                  </span>
                </div>
                <div className="p-3 text-xs">
                  <p className="text-muted-foreground font-mono mb-2">
                    {compareData.persistent_findings?.length
                      ? `${compareData.persistent_findings.length} defect(s) remain unresolved across revisions.`
                      : 'All prior revision defects addressed.'}
                  </p>
                  {compareData.persistent_findings && compareData.persistent_findings.length > 0 && (
                    <div className="divide-y divide-border/50">
                      {compareData.persistent_findings.map(f => (
                        <div key={f.id} className="py-2 flex items-start gap-2">
                          <span className="font-mono text-xs text-muted-foreground bg-secondary border border-border px-1.5 py-0.2 rounded-sm shrink-0">
                            {f.rule_id}
                          </span>
                          <span className="text-foreground">{f.explanation}</span>
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
    </>
  )
}
