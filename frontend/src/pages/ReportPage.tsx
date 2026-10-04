import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { submissionsApi, reportsApi } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ArrowLeft, Download, CheckCircle, XCircle, Link2 } from 'lucide-react'
import { formatDate, scoreColor, severityBadgeVariant } from '@/lib/utils'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip
} from 'recharts'

type Tab = 'scores' | 'findings' | 'traceability'

export default function ReportPage() {
  const { id } = useParams<{ id: string }>()
  const { isInstructor } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<Tab>('scores')
  const [decisionMap, setDecisionMap] = useState<Record<number, { status: string; comment: string }>>({})

  const submissionId = Number(id)

  const { data: subRes } = useQuery({
    queryKey: ['submission', id],
    queryFn: () => submissionsApi.get(submissionId)
  })

  const { data: scoresRes } = useQuery({
    queryKey: ['scores', id],
    queryFn: () => reportsApi.scores(submissionId),
    enabled: !!id
  })

  const { data: findingsRes } = useQuery({
    queryKey: ['findings', id],
    queryFn: () => reportsApi.findings(submissionId),
    enabled: !!id
  })

  const { data: traceRes } = useQuery({
    queryKey: ['traceability', id],
    queryFn: () => reportsApi.traceability(submissionId),
    enabled: !!id
  })

  const decisionMutation = useMutation({
    mutationFn: ({ findingId, data }: { findingId: number; data: { status: string; comment?: string } }) =>
      reportsApi.makeDecision(submissionId, findingId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['findings', id] })
  })

  const traceLinkMutation = useMutation({
    mutationFn: ({ linkId, status }: { linkId: number; status: string }) =>
      reportsApi.updateTraceLink(submissionId, linkId, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['traceability', id] })
  })

  const submission = subRes?.data
  const scores = scoresRes?.data
  const findings = findingsRes?.data || []
  const traceLinks = traceRes?.data || []

  const radarData = scores && scores.overall_score !== undefined ? [
    { subject: 'Requirements', value: (scores.requirements_score / 40) * 100 },
    { subject: 'UML', value: (scores.uml_score / 30) * 100 },
    { subject: 'Traceability', value: (scores.traceability_score / 30) * 100 },
  ] : []

  const handleExportCSV = () => {
    if (!traceLinks.length) return
    const header = 'Source Type,Source ID,Target Type,Target ID,Status\n'
    const rows = traceLinks.map((l: any) =>
      `${l.source_type},${l.source_id},${l.target_type},${l.target_id},${l.status}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `traceability-${submissionId}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'scores', label: 'Scores' },
    { key: 'findings', label: `Findings (${findings.length})` },
    { key: 'traceability', label: 'Traceability' },
  ]

  return (
    <div className="p-8">
      <Link to="/submissions" className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm print:hidden">
        <ArrowLeft className="h-4 w-4" /> Back to Submissions
      </Link>

      {submission && (
        <div className="mb-6">
          <h1 className="text-3xl font-bold">{submission.team_name}</h1>
          <p className="text-gray-500">Version {submission.version} • {formatDate(submission.created_at)}</p>
          <Badge variant={submission.status === 'done' ? 'default' : submission.status === 'error' ? 'destructive' : 'outline'}
            className="mt-2">{submission.status}</Badge>
        </div>
      )}

      {/* Tab nav */}
      <div className="flex gap-1 border-b border-gray-200 mb-6 print:hidden">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Scores Tab */}
      {activeTab === 'scores' && scores && scores.overall_score !== undefined && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader><CardTitle>Overall Score</CardTitle></CardHeader>
            <CardContent>
              <div className="text-center py-4">
                <p className={`text-6xl font-bold ${scoreColor(scores.overall_score)}`}>
                  {scores.overall_score}
                </p>
                <p className="text-gray-500 mt-2">out of 100</p>
              </div>
              <div className="space-y-3 mt-4">
                {[
                  { label: 'Requirements (40%)', val: scores.requirements_score, max: 40 },
                  { label: 'UML (30%)', val: scores.uml_score, max: 30 },
                  { label: 'Traceability (30%)', val: scores.traceability_score, max: 30 },
                ].map(({ label, val, max }) => (
                  <div key={label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{label}</span>
                      <span className={`font-medium ${scoreColor((val / max) * 100)}`}>{val}/{max}</span>
                    </div>
                    <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${(val / max) * 100 >= 80 ? 'bg-green-500' : (val / max) * 100 >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${(val / max) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Quality Radar</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" tick={{ fontSize: 12 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
                  <Radar name="Score" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'scores' && scores && scores.message && (
        <Card><CardContent className="p-6 text-center text-gray-500">{scores.message} (Status: {scores.status})</CardContent></Card>
      )}

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div className="space-y-4">
          {findings.length === 0 && (
            <p className="text-gray-500 text-center py-8">No findings detected.</p>
          )}
          {findings.map((f: any) => {
            const existingDecision = f.instructor_decision
            const dec = decisionMap[f.id] || { status: existingDecision?.status || '', comment: existingDecision?.comment || '' }
            return (
              <Card key={f.id} className={`border-l-4 ${
                f.severity === 'critical' ? 'border-l-red-500' :
                f.severity === 'major' ? 'border-l-orange-500' : 'border-l-yellow-400'
              }`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={severityBadgeVariant(f.severity)}>{f.severity}</Badge>
                        <Badge variant="outline">{f.rule_id}</Badge>
                        {f.artifact_type && <Badge variant="outline">{f.artifact_type}</Badge>}
                        {f.requirement_id && (
                          <span className="text-xs text-gray-400">REQ: {f.requirement_id}</span>
                        )}
                      </div>
                      <p className="text-gray-900">{f.explanation}</p>
                      {f.quoted_text && (
                        <p className="text-sm text-gray-500 mt-1 italic border-l-2 border-gray-200 pl-3">"{f.quoted_text}"</p>
                      )}
                      {f.rewrite_suggestion && (
                        <p className="text-sm text-blue-600 mt-2 italic">💡 {f.rewrite_suggestion}</p>
                      )}
                    </div>
                    {existingDecision && (
                      <div className="shrink-0">
                        {existingDecision.status === 'accepted' && <CheckCircle className="h-5 w-5 text-green-500" />}
                        {existingDecision.status === 'rejected' && <XCircle className="h-5 w-5 text-red-500" />}
                      </div>
                    )}
                  </div>

                  {isInstructor && !existingDecision && (
                    <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
                      <div className="flex gap-2">
                        <Select
                          value={dec.status}
                          onValueChange={v => setDecisionMap(d => ({ ...d, [f.id]: { ...dec, status: v } }))}
                        >
                          <SelectTrigger className="w-40">
                            <SelectValue placeholder="Decision" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="accepted">Accept</SelectItem>
                            <SelectItem value="rejected">Reject</SelectItem>
                          </SelectContent>
                        </Select>
                        <Button
                          size="sm"
                          disabled={!dec.status || decisionMutation.isPending}
                          onClick={() => decisionMutation.mutate({
                            findingId: f.id,
                            data: { status: dec.status, comment: dec.comment }
                          })}
                        >
                          Save
                        </Button>
                      </div>
                      <Textarea
                        placeholder="Optional comment..."
                        value={dec.comment}
                        onChange={e => setDecisionMap(d => ({ ...d, [f.id]: { ...dec, comment: e.target.value } }))}
                        className="text-sm"
                        rows={2}
                      />
                    </div>
                  )}

                  {existingDecision?.comment && (
                    <div className="mt-3 pt-3 border-t border-gray-100">
                      <p className="text-sm text-gray-500">
                        <span className="font-medium capitalize">{existingDecision.status}</span>: {existingDecision.comment}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Traceability Tab */}
      {activeTab === 'traceability' && (
        <div>
          <div className="flex justify-end mb-4">
            <Button variant="outline" onClick={handleExportCSV}>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>

          {traceLinks.length > 0 ? (
            <Card>
              <CardHeader><CardTitle>Trace Links ({traceLinks.length})</CardTitle></CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-gray-500">
                        <th className="pb-3 pr-4">Source</th>
                        <th className="pb-3 pr-4">→</th>
                        <th className="pb-3 pr-4">Target</th>
                        <th className="pb-3 pr-4">Status</th>
                        {isInstructor && <th className="pb-3">Action</th>}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {traceLinks.map((link: any) => (
                        <tr key={link.id}>
                          <td className="py-3 pr-4">
                            <span className="font-mono text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                              {link.source_type}: {link.source_id}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-gray-400">
                            <Link2 className="h-4 w-4" />
                          </td>
                          <td className="py-3 pr-4">
                            <span className="font-mono text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                              {link.target_type}: {link.target_id}
                            </span>
                          </td>
                          <td className="py-3 pr-4">
                            <Badge variant={
                              link.status === 'confirmed' ? 'default' :
                              link.status === 'rejected' ? 'destructive' : 'outline'
                            }>
                              {link.status}
                            </Badge>
                          </td>
                          {isInstructor && (
                            <td className="py-3">
                              <div className="flex gap-1">
                                <Button size="sm" variant="ghost"
                                  onClick={() => traceLinkMutation.mutate({ linkId: link.id, status: 'confirmed' })}>
                                  ✓
                                </Button>
                                <Button size="sm" variant="ghost"
                                  onClick={() => traceLinkMutation.mutate({ linkId: link.id, status: 'rejected' })}>
                                  ✗
                                </Button>
                              </div>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <Link2 className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p>No trace links found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

