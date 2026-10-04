import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { projectsApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Upload, ArrowLeft, X, FileText } from 'lucide-react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [srsFile, setSrsFile] = useState<File | null>(null)
  
  const [umlFiles, setUmlFiles] = useState<{ type: string; file: File }[]>([])
  const [umlType, setUmlType] = useState('usecase')
  const [umlFile, setUmlFile] = useState<File | null>(null)
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAddUml = () => {
    if (umlFile) {
      setUmlFiles([...umlFiles, { type: umlType, file: umlFile }])
      setUmlFile(null)
    }
  }

  const handleUploadAndAnalyze = async () => {
    if (!name || !srsFile) {
      setError("Project Name and SRS document are required.")
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await projectsApi.create({ name, description })
      const projectId = res.data.id

      await projectsApi.uploadSRS(projectId, srsFile)
      
      for (const uml of umlFiles) {
        await projectsApi.uploadUML(projectId, uml.type, uml.file)
      }

      await projectsApi.analyze(projectId)
      navigate(`/projects/${projectId}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create project and start analysis.')
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <Link to="/projects" className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-6 text-sm">
        <ArrowLeft className="h-4 w-4" /> Back to Projects
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Analyze New Project</h1>
        <p className="text-slate-500 mt-2">Upload your Software Requirements Specification (SRS) and UML diagrams to get instant AI-powered feedback.</p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Project Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && <div className="p-3 bg-red-50 text-red-600 text-sm rounded-md">{error}</div>}
          
          <div className="space-y-2">
            <Label>Project Name *</Label>
            <Input placeholder="e.g., E-Commerce Platform V2" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Description (Optional)</Label>
            <Textarea placeholder="Brief summary of this project..." value={description} onChange={e => setDescription(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>
        <CardContent className="space-y-8">
          <div>
            <Label className="text-base font-medium mb-3 block">SRS Document *</Label>
            <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center hover:bg-slate-50 transition-colors">
              <Upload className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <Input type="file" accept=".pdf,.docx" onChange={e => setSrsFile(e.target.files?.[0] || null)} className="max-w-xs mx-auto mb-2" />
              {srsFile && <p className="text-sm text-green-600 font-medium">✓ {srsFile.name}</p>}
            </div>
          </div>

          <div>
            <Label className="text-base font-medium mb-3 block">UML Diagrams (Optional)</Label>
            <p className="text-sm text-gray-500 mb-4">Upload PlantUML text files (.txt, .puml) to enable architecture validation.</p>
            
            <div className="flex gap-4 mb-4">
              <Select value={umlType} onValueChange={setUmlType}>
                <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="usecase">Use Case Diagram</SelectItem>
                  <SelectItem value="class">Class Diagram</SelectItem>
                  <SelectItem value="sequence">Sequence Diagram</SelectItem>
                </SelectContent>
              </Select>
              <Input type="file" accept=".txt,.puml" onChange={e => setUmlFile(e.target.files?.[0] || null)} className="flex-1" />
              <Button type="button" variant="secondary" onClick={handleAddUml} disabled={!umlFile}>Add</Button>
            </div>

            {umlFiles.length > 0 && (
              <ul className="space-y-2">
                {umlFiles.map((u, i) => (
                  <li key={i} className="flex justify-between items-center p-3 bg-gray-50 rounded-md border text-sm">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-500" />
                      <span className="font-medium">[{u.type}]</span> {u.file.name}
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => setUmlFiles(fs => fs.filter((_, idx) => idx !== i))}>
                      <X className="h-4 w-4 text-red-500" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </CardContent>
      </Card>

      <Button size="lg" onClick={handleUploadAndAnalyze} disabled={loading || !name || !srsFile} className="w-full text-lg h-12">
        {loading ? 'Uploading & Analyzing...' : 'Run Analysis'}
      </Button>
    </div>
  )
}
