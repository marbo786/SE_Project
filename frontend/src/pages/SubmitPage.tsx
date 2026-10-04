import React, { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { submissionsApi } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Upload, Plus, X, ArrowLeft } from 'lucide-react'

export default function SubmitPage() {
  const { id: assignmentId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [teamName, setTeamName] = useState('')
  const [members, setMembers] = useState([''])
  const [srsFile, setSrsFile] = useState<File | null>(null)
  const [umlFiles, setUmlFiles] = useState<{ type: string; file: File }[]>([])
  const [umlType, setUmlType] = useState('usecase')
  const [umlFile, setUmlFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'form' | 'upload' | 'done'>('form')
  const [submissionId, setSubmissionId] = useState<number | null>(null)

  const addMember = () => setMembers(m => [...m, ''])
  const removeMember = (i: number) => setMembers(m => m.filter((_, idx) => idx !== i))
  const updateMember = (i: number, val: string) => setMembers(m => m.map((v, idx) => idx === i ? val : v))

  const handleCreateSubmission = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await submissionsApi.create({
        assignment_id: parseInt(assignmentId!),
        team_name: teamName,
        member_names: members.filter(Boolean)
      } as any)
      setSubmissionId(res.data.id)
      setStep('upload')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create submission')
    } finally {
      setLoading(false)
    }
  }

  const addUmlFile = () => {
    if (umlFile) {
      setUmlFiles(f => [...f, { type: umlType, file: umlFile }])
      setUmlFile(null)
    }
  }

  const handleUploadAndAnalyze = async () => {
    if (!submissionId || !srsFile) return
    setLoading(true)
    setError('')
    try {
      await submissionsApi.uploadSRS(submissionId, srsFile)
      for (const uml of umlFiles) {
        await submissionsApi.uploadUML(submissionId, uml.type, uml.file)
      }
      await submissionsApi.analyze(submissionId)
      setStep('done')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload/analysis failed')
    } finally {
      setLoading(false)
    }
  }

  if (step === 'done') {
    return (
      <div className="p-8 max-w-2xl mx-auto">
        <div className="text-center py-16">
          <div className="text-5xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold mb-2">Analysis Started!</h2>
          <p className="text-gray-500 mb-6">Your submission is being analyzed. Check back shortly for results.</p>
          <Button onClick={() => navigate(`/submissions/${submissionId}`)}>
            View Report
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <Link to={`/assignments/${assignmentId}`} className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </Link>
      <h1 className="text-2xl font-bold mb-6">New Submission</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-md text-sm mb-4">
          {error}
        </div>
      )}

      {step === 'form' && (
        <Card>
          <CardHeader><CardTitle>Team Information</CardTitle></CardHeader>
          <CardContent>
            <form onSubmit={handleCreateSubmission} className="space-y-4">
              <div className="space-y-2">
                <Label>Team Name</Label>
                <Input placeholder="Team Alpha" value={teamName}
                  onChange={e => setTeamName(e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label>Team Members</Label>
                {members.map((m, i) => (
                  <div key={i} className="flex gap-2">
                    <Input placeholder={`Member ${i + 1}`} value={m}
                      onChange={e => updateMember(i, e.target.value)} />
                    {members.length > 1 && (
                      <Button type="button" variant="ghost" size="icon"
                        onClick={() => removeMember(i)}>
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                <Button type="button" variant="outline" size="sm" onClick={addMember}>
                  <Plus className="h-4 w-4 mr-2" /> Add Member
                </Button>
              </div>
              <Button type="submit" disabled={loading}>
                {loading ? 'Creating...' : 'Continue'}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {step === 'upload' && (
        <Card>
          <CardHeader><CardTitle>Upload Documents</CardTitle></CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label>SRS Document (PDF) *</Label>
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
                <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                <Input type="file" accept=".pdf,.docx"
                  onChange={e => setSrsFile(e.target.files?.[0] || null)}
                  className="max-w-xs mx-auto" />
                {srsFile && <p className="text-sm text-green-600 mt-2">✓ {srsFile.name}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label>UML Diagrams (optional)</Label>
              <div className="flex gap-2">
                <Select value={umlType} onValueChange={setUmlType}>
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="usecase">Use Case</SelectItem>
                    <SelectItem value="class">Class</SelectItem>
                    <SelectItem value="sequence">Sequence</SelectItem>
                    
                    
                  </SelectContent>
                </Select>
                <Input type="file" accept=".puml,.plantuml,.txt"
                  onChange={e => setUmlFile(e.target.files?.[0] || null)}
                  className="flex-1" />
                <Button type="button" variant="outline" onClick={addUmlFile} disabled={!umlFile}>
                  Add
                </Button>
              </div>
              {umlFiles.length > 0 && (
                <ul className="text-sm space-y-1 mt-2">
                  {umlFiles.map((u, i) => (
                    <li key={i} className="flex items-center gap-2 text-green-600">
                      ✓ [{u.type}] {u.file.name}
                      <button onClick={() => setUmlFiles(f => f.filter((_, idx) => idx !== i))}
                        className="text-red-400 hover:text-red-600 ml-auto">
                        <X className="h-3 w-3" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <Button onClick={handleUploadAndAnalyze} disabled={loading || !srsFile} className="w-full">
              {loading ? 'Uploading & Analyzing...' : 'Submit & Analyze'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
