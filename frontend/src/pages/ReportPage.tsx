import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { projectsApi, findingsApi, traceabilityApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowLeft, CheckCircle, XCircle, Link2, Download, AlertCircle, History, BadgeCheck } from 'lucide-react'

export default function ReportPage() {
  const { id } = useParams()
  const projectId = Number(id)
  
  const [project, setProject] = useState<any>(null)
  const [findings, setFindings] = useState<any[]>([])
  const [traceLinks, setTraceLinks] = useState<any[]>([])
  const [scores, setScores] = useState<any>(null)
  const [compareData, setCompareData] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('scores')

    const fetchTraceLinks = () => traceabilityApi.getByProject(projectId).then(res => setTraceLinks(res.data))
    
    useEffect(() => {
      projectsApi.get(projectId).then(res => {
        setProject(res.data)
        if (res.data.version > 1) {
          projectsApi.compare(projectId, res.data.version - 1).then(cRes => setCompareData(cRes.data)).catch(() => {})
        }
      })
      findingsApi.getByProject(projectId).then(res => setFindings(res.data))
      fetchTraceLinks()
    }, [projectId])

    const updateLinkStatus = async (linkId: number, status: string) => {
        try {
            const token = localStorage.getItem('token');
            await fetch(`http://localhost:8000/traceability/${linkId}`, {
                method: 'PATCH',
                headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            fetchTraceLinks();
        } catch (e) {
            console.error(e);
        }
    }
    
    const downloadTraceability = () => {
        const token = localStorage.getItem('token');
        fetch(`http://localhost:8000/traceability/project/${projectId}/export`, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `traceability_${projectId}.csv`;
            a.click();
        });
    }
    
    // Quick and dirty fetch for scores from findings list just for the UI
    // The backend computes it in QualityScore, but we can just use the project's state.
  }, [projectId])

  const formatDate = (d: string) => new Date(d).toLocaleString()

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <Link to="/projects" className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm print:hidden">
        <ArrowLeft className="h-4 w-4" /> Back to Projects
      </Link>

      {project && (
        <div className="mb-6 flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold">{project.name}</h1>
            <p className="text-gray-500">Version {project.version} • {formatDate(project.created_at)}</p>
            <Badge variant={project.status === 'done' ? 'default' : project.status === 'error' ? 'destructive' : 'outline'} className="mt-2">
              {project.status.toUpperCase()}
            </Badge>
          </div>
          <Button onClick={() => window.print()} className="print:hidden">
            <Download className="mr-2 h-4 w-4" /> Download PDF
          </Button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b border-gray-200 mb-6 print:hidden">
        {['scores', 'findings', 'traceability', 'compare'].map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-4 py-2 font-medium capitalize transition-colors border-b-2 ${
              activeTab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-900'
            }`}
          >
            {t === 'compare' ? 'Version History' : t}
          </button>
        ))}
      </div>

      {/* Scores */}
      <div className={activeTab === 'scores' ? "block" : "hidden print:block"}>
        <h2 className="text-2xl font-bold mb-4 hidden print:block">Quality Scores</h2>
        <Card>
          <CardContent className="p-6 text-center">
            <h3 className="text-lg font-medium text-gray-600">Overall Quality</h3>
            <div className="text-5xl font-bold mt-4 text-blue-600">
              {project?.status === 'done' ? 'Analyzed' : 'Pending'}
            </div>
            <p className="text-sm text-gray-500 mt-4">This project has {findings.length} total findings.</p>
          </CardContent>
        </Card>
      </div>

      {/* Findings */}
      <div className={activeTab === 'findings' ? "block mt-8" : "hidden print:block print:mt-8"}>
        <h2 className="text-2xl font-bold mb-4 hidden print:block">Analysis Findings</h2>
        <div className="space-y-4">
          {findings.length === 0 ? <p className="text-gray-500 text-center py-8 border rounded-lg">No findings recorded.</p> : (
            findings.map((f: any) => (
              <Card key={f.id} className="border-l-4 border-l-blue-500">
                <CardContent className="p-6">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">{f.severity.toUpperCase()}</Badge>
                    <Badge variant="secondary">{f.rule_id}</Badge>
                    {f.artifact_type && <Badge variant="secondary">{f.artifact_type}</Badge>}
                  </div>
                  <p className="font-medium text-slate-900">{f.explanation}</p>
                  {f.quoted_text && (
                    <blockquote className="mt-2 text-sm text-gray-500 italic border-l-2 border-gray-200 pl-3">
                      "{f.quoted_text}"
                    </blockquote>
                  )}
                  {f.rewrite_suggestion && (
                    <p className="text-sm text-blue-600 mt-3 font-medium bg-blue-50 p-3 rounded-md">
                      💡 Suggestion: {f.rewrite_suggestion}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Traceability */}
      <div className={activeTab === 'traceability' ? "block mt-8" : "hidden print:block print:mt-8"}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold hidden print:block">Traceability Matrix</h2>
          <button onClick={downloadTraceability} className="px-4 py-2 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 print:hidden">Download CSV</button>
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="bg-slate-50 border-b">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Source</th>
                    <th className="px-6 py-3 font-semibold text-center">Status</th>
                    <th className="px-6 py-3 font-semibold">Target</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {traceLinks.length === 0 ? <tr><td colSpan={3} className="px-6 py-8 text-center text-gray-500">No trace links generated.</td></tr> : (
                    traceLinks.map((t: any) => (
                      <tr key={t.id}>
                        <td className="px-6 py-4">
                          <span className="font-medium">{t.source_id}</span> ({t.source_type})
                        </td>
                        <td className="px-6 py-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <span className={px-2 py-1 text-xs rounded-full \}>{t.status}</span>
                            {t.status === 'suggested' && (
                                <div className="flex flex-col gap-1 print:hidden">
                                    <button onClick={() => updateLinkStatus(t.id, 'confirmed')} className="px-2 py-1 bg-green-500 text-white rounded text-xs hover:bg-green-600">Confirm</button>
                                    <button onClick={() => updateLinkStatus(t.id, 'rejected')} className="px-2 py-1 bg-red-500 text-white rounded text-xs hover:bg-red-600">Reject</button>
                                </div>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="font-medium">{t.target_id}</span> ({t.target_type})
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Compare Tab */}
      <div className={activeTab === 'compare' ? "block mt-8" : "hidden print:block print:mt-8"}>
        <h2 className="text-2xl font-bold mb-4 hidden print:block">Version History</h2>
        {!compareData ? (
          <p className="text-gray-500 py-8 text-center border rounded-lg">No previous version data available to compare against.</p>
        ) : (
          <div className="space-y-6">
            <Card className="border-l-4 border-l-green-500">
              <CardHeader><CardTitle className="flex items-center gap-2"><BadgeCheck className="text-green-500" /> Resolved Findings ({compareData.resolved_findings?.length || 0})</CardTitle></CardHeader>
              <CardContent>
                {compareData.resolved_findings?.length === 0 ? <p className="text-gray-500">No findings were resolved.</p> : (
                  <ul className="space-y-3">
                    {compareData.resolved_findings?.map((f: any) => (
                      <li key={f.id} className="text-sm border-b pb-2">
                        <Badge variant="outline" className="mr-2">{f.rule_id}</Badge>
                        <span className="text-gray-700">{f.explanation}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-red-500">
              <CardHeader><CardTitle className="flex items-center gap-2"><AlertCircle className="text-red-500" /> New Findings ({compareData.new_findings?.length || 0})</CardTitle></CardHeader>
              <CardContent>
                {compareData.new_findings?.length === 0 ? <p className="text-gray-500">No new findings introduced.</p> : (
                  <ul className="space-y-3">
                    {compareData.new_findings?.map((f: any) => (
                      <li key={f.id} className="text-sm border-b pb-2">
                        <Badge variant="outline" className="mr-2">{f.rule_id}</Badge>
                        <span className="text-gray-700">{f.explanation}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
            
            <Card className="border-l-4 border-l-yellow-500">
              <CardHeader><CardTitle className="flex items-center gap-2"><History className="text-yellow-500" /> Persistent Findings ({compareData.persistent_findings?.length || 0})</CardTitle></CardHeader>
              <CardContent>
                <p className="text-sm text-gray-500">These findings were present in the previous version and have not yet been fixed.</p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

    </div>
  )
}
