import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { historyApi, apiError, Revision } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { PageHeader, Breadcrumbs } from '@/components/ui/page-header'
import { cn } from '@/lib/utils'
import {
  Upload,
  ArrowLeft,
  ArrowRight,
  X,
  FileText,
  AlertCircle,
  FileCode,
  Check,
} from 'lucide-react'

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

export default function NewProjectPage() {
  const navigate = useNavigate()
  const srsInputRef = useRef<HTMLInputElement>(null)
  const umlInputRef = useRef<HTMLInputElement>(null)

  // Step indicator (1 to 4)
  const [currentStep, setCurrentStep] = useState<number>(1)

  // Form State
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [profile, setProfile] = useState<'srs_only' | 'architecture'>('srs_only')
  const [useAI, setUseAI] = useState(false)
  const [srsFile, setSrsFile] = useState<File | null>(null)

  // UML Diagrams
  const [umlFiles, setUmlFiles] = useState<{ type: string; file: File }[]>([])
  const [umlType, setUmlType] = useState('usecase')
  const [umlFile, setUmlFile] = useState<File | null>(null)

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false)

  // Status
  const [progress, setProgress] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const savedProject = useRef<{ id: number; current_revision_id: number } | null>(null)
  const createKey = useRef(crypto.randomUUID())
  const uploaded = useRef(new Set<File>())
  const attempts = useRef(new Map<File, { key: string; revision: Revision; replaceId?: number }>())

  const handleAddUml = () => {
    if (umlFile) {
      setUmlFiles([...umlFiles, { type: umlType, file: umlFile }])
      setUmlFile(null)
      if (umlInputRef.current) umlInputRef.current.value = ''
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase()
      if (ext === '.pdf' || ext === '.docx') {
        setSrsFile(file)
        setError('')
      } else {
        setError('Unsupported format. Please provide a .pdf or .docx file.')
      }
    }
  }

  const handleUploadAndAnalyze = async () => {
    if (!name.trim()) {
      setError('Specification name is required.')
      setCurrentStep(1)
      return
    }
    if (!srsFile) {
      setError('SRS document (.pdf or .docx) is required.')
      setCurrentStep(2)
      return
    }
    if (profile === 'architecture' && !['usecase', 'class', 'sequence'].every(type => umlFiles.some(uml => uml.type === type))) {
      setError('The architecture profile requires use-case, class, and sequence diagrams.')
      setCurrentStep(3)
      return
    }

    if ([srsFile, ...umlFiles.map(item => item.file)].some(file => file.size > 10 * 1024 * 1024)) { setError('Each file must be smaller than 10 MB.'); return }
    setLoading(true)
    setError('')

    try {
      if (!savedProject.current) {
        const response = await historyApi.create({ name, description, analysis_profile: profile, analysis_mode: useAI ? 'ai' : 'deterministic' }, createKey.current)
        savedProject.current = response.data
      }
      const project = savedProject.current!
      let revision = (await historyApi.revision(project.id, project.current_revision_id)).data
      for (const input of [{ type: 'srs', file: srsFile }, ...umlFiles.map(uml => ({ type: `uml_${uml.type}`, file: uml.file }))]) {
        if (uploaded.current.has(input.file)) continue
        if (!attempts.current.has(input.file)) attempts.current.set(input.file, { key: crypto.randomUUID(), revision,
          replaceId: input.type === 'srs' ? revision.artifacts.find(a => a.type === 'srs')?.id : undefined })
        const attempt = attempts.current.get(input.file)!
        const response = await historyApi.upload(project.id, attempt.revision, input.type, input.file, attempt.key, attempt.replaceId, percent => setProgress(`${input.file.name}: ${percent === 100 ? 'validating source' : `uploading ${percent}%`}`))
        uploaded.current.add(input.file)
        revision = response.data.revision
      }
      navigate(`/projects/${project.id}/revisions/${revision.id}`)
    } catch (err: any) {
      setError(apiError(err, 'The draft could not be saved. Retry to continue the same project.') + (savedProject.current ? ' Your saved draft is also available in Projects.' : ''))
      setLoading(false)
    }
  }

  const steps = [
    { num: 1, label: 'Project details' },
    { num: 2, label: 'SRS Document' },
    { num: 3, label: 'Architecture UML' },
    { num: 4, label: 'Save draft' },
  ]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {loading && <p role="status">{progress || 'Saving project…'}</p>}
      {/* Navigation Breadcrumb */}
      <Breadcrumbs
        items={[
          { label: 'Specifications', href: '/projects' },
          { label: 'New specification' },
        ]}
      />

      <PageHeader
        title="New specification"
        description="Upload your source documents, review the extracted requirements, then start an analysis."
      />

      {/* Step Navigation Bar */}
      <div className="flex border border-border rounded bg-secondary text-xs font-mono overflow-hidden">
        {steps.map(step => {
          const active = currentStep === step.num
          const complete = currentStep > step.num
          return (
            <button
              key={step.num}
              onClick={() => setCurrentStep(step.num)}
              className={cn(
                "flex-1 py-2 px-3 text-left border-r border-border last:border-r-0 flex items-center gap-2 transition-none",
                active && "bg-card text-foreground font-medium border-b-2 border-b-primary",
                complete && "text-success",
                !active && !complete && "text-muted-foreground hover:text-muted-foreground"
              )}
            >
              <span className={cn(
                "w-4 h-4 rounded-sm flex items-center justify-center text-xs",
                active ? "bg-primary text-background font-bold" : complete ? "bg-success/20 text-success" : "bg-accent text-muted-foreground"
              )}>
                {complete ? '✓' : step.num}
              </span>
              <span className="truncate">{step.label}</span>
            </button>
          )
        })}
      </div>

      {/* Error alert banner */}
      {error && (
        <div className="p-3 rounded border border-danger/40 bg-danger/10 text-xs text-danger flex items-center gap-2 font-mono">
          <AlertCircle className="h-4 w-4 shrink-0 text-danger" />
          <span>{error}</span>
        </div>
      )}

      {/* STEP 1: Project Details */}
      {currentStep === 1 && (
        <div className="rounded border border-border bg-card p-4 space-y-4">
          <div className="border-b border-border pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              Step 1: Specification Scope & Identification
            </h3>
          </div>

          <div className="space-y-3">
            <div className="space-y-2">
              <Label htmlFor="analysis-profile">What should this review cover?</Label>
              <select id="analysis-profile" value={profile} onChange={event => setProfile(event.target.value as typeof profile)} className="block w-full rounded border border-border bg-secondary p-3 text-sm">
                <option value="srs_only">Requirements only</option>
                <option value="architecture">Requirements and architecture (all three UML diagrams)</option>
              </select>
              <p className="text-sm text-muted-foreground">The selected scope determines which checks and scores apply. Requirements-only reviews do not grade UML or traceability.</p>
              <label className="flex items-start gap-3 text-sm"><input type="checkbox" checked={useAI} onChange={event => setUseAI(event.target.checked)} className="mt-1" />Include AI suggestions using the configured provider. Deterministic checks work offline.</label>
            </div>
            <div>
              <Label htmlFor="spec-name" className="text-xs text-foreground mb-1.5 block">
                Specification Name <span className="text-danger">*</span>
              </Label>
              <Input
                id="spec-name"
                placeholder="e.g. Flight Navigation System SRS"
                value={name}
                onChange={e => setName(e.target.value)}
                autoFocus
              />
              <p className="text-xs text-muted-foreground mt-1">
                Unique identifier for tracking requirement versions over time.
              </p>
            </div>

            <div>
              <Label htmlFor="spec-desc" className="text-xs text-foreground mb-1.5 block">
                Description / Scope (Optional)
              </Label>
              <Textarea
                id="spec-desc"
                placeholder="Brief summary of requirements scope, target subsystems, or revision notes..."
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={3}
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <Button
              onClick={() => {
                if (!name.trim()) {
                  setError('Specification Name is required.')
                  return
                }
                setError('')
                setCurrentStep(2)
              }}
            >
              Continue to Document Upload
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 2: Upload SRS Document */}
      {currentStep === 2 && (
        <div className="rounded border border-border bg-card p-4 space-y-4">
          <div className="border-b border-border pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              Step 2: Requirements document
            </h3>
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            role="button"
            tabIndex={0}
            aria-label="Choose SRS document"
            onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); srsInputRef.current?.click() } }}
            onClick={() => srsInputRef.current?.click()}
            className={cn(
              "border border-dashed rounded p-6 text-center cursor-pointer transition-none",
              isDragging
                ? "border-primary bg-primary/10"
                : "border-border bg-secondary hover:border-primary/50 hover:bg-card"
            )}
          >
            <input
              ref={srsInputRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={e => {
                if (e.target.files && e.target.files[0]) {
                  setSrsFile(e.target.files[0])
                  setError('')
                }
              }}
            />
            <Upload className="h-6 w-6 mx-auto mb-2 text-primary" />
            <p className="text-xs font-medium text-foreground mb-1">
              Select or drop specification document
            </p>
            <p className="text-xs font-mono text-muted-foreground">
              Supported file formats: .PDF, .DOCX
            </p>
          </div>

          {/* Selected File Details */}
          {srsFile && (
            <div className="flex items-center justify-between p-2.5 rounded border border-border bg-secondary">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="h-4 w-4 text-primary shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-mono font-medium text-foreground truncate">{srsFile.name}</p>
                  <p className="text-xs font-mono text-muted-foreground">{formatFileSize(srsFile.size)}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-muted-foreground hover:text-danger"
                aria-label="Remove SRS file"
                onClick={() => setSrsFile(null)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          <div className="pt-2 flex justify-between">
            <Button variant="outline" onClick={() => setCurrentStep(1)}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Back
            </Button>
            <Button
              onClick={() => {
                if (!srsFile) {
                  setError('Please select an SRS document before continuing.')
                  return
                }
                setError('')
                setCurrentStep(3)
              }}
            >
              Continue to UML Diagrams
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 3: Add UML Diagrams */}
      {currentStep === 3 && (
        <div className="rounded border border-border bg-card p-4 space-y-4">
          <div className="border-b border-border pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              Step 3: Architecture Diagram Models (Optional)
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Attach PlantUML diagram models (.puml, .txt) to generate requirement-to-architecture traceability matrices.
            </p>
          </div>

          <div className="p-3 rounded border border-border bg-secondary space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div>
                <Label className="text-xs text-muted-foreground mb-1 block">Diagram Type</Label>
                <Select value={umlType} onValueChange={setUmlType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="usecase">Use Case Diagram</SelectItem>
                    <SelectItem value="class">Class Diagram</SelectItem>
                    <SelectItem value="sequence">Sequence Diagram</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="sm:col-span-2">
                <Label className="text-xs text-muted-foreground mb-1 block">PlantUML Model File</Label>
                <div className="flex gap-2">
                  <input
                    aria-label="PlantUML file"
                    ref={umlInputRef}
                    type="file"
                    accept=".txt,.puml"
                    className="text-xs text-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border file:border-border file:bg-card file:text-xs file:text-foreground file:cursor-pointer flex-1"
                    onChange={e => setUmlFile(e.target.files?.[0] || null)}
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={handleAddUml}
                    disabled={!umlFile}
                  >
                    Add Model
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* Attached Diagrams List */}
          {umlFiles.length > 0 ? (
            <div className="space-y-1.5">
              <p className="text-xs font-mono uppercase text-muted-foreground">
                Attached Architecture Models ({umlFiles.length})
              </p>
              <div className="divide-y divide-border border border-border rounded bg-secondary overflow-hidden">
                {umlFiles.map((item, idx) => (
                  <div key={idx} className="p-2 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0 font-mono">
                      <FileCode className="h-3.5 w-3.5 text-primary shrink-0" />
                      <Badge variant="outline" className="text-xs uppercase">
                        {item.type}
                      </Badge>
                      <span className="text-foreground truncate">{item.file.name}</span>
                      <span className="text-xs text-muted-foreground">({formatFileSize(item.file.size)})</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-1 text-muted-foreground hover:text-danger"
                      aria-label={`Remove ${item.file.name}`}
                      onClick={() => setUmlFiles(umlFiles.filter((_, i) => i !== idx))}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No architecture models attached. You may continue without UML models.
            </p>
          )}

          <div className="pt-2 flex justify-between">
            <Button variant="outline" onClick={() => setCurrentStep(2)}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Back
            </Button>
            <Button onClick={() => setCurrentStep(4)}>
              Review files and scope
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 4: Review and Execute Ingestion */}
      {currentStep === 4 && (
        <div className="rounded border border-border bg-card p-4 space-y-4">
          <div className="border-b border-border pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-muted-foreground">
              Step 4: Confirm files and scope
            </h3>
          </div>

          <div className="divide-y divide-border border border-border rounded bg-secondary text-xs font-mono">
            <div className="p-3 flex items-center justify-between">
              <span className="text-muted-foreground">SPECIFICATION IDENTIFIER</span>
              <span className="text-foreground font-medium">{name}</span>
            </div>

            {description && (
              <div className="p-3 flex items-start justify-between">
                <span className="text-muted-foreground">SCOPE / DESCRIPTION</span>
                <span className="text-foreground max-w-sm text-right font-sans text-xs">{description}</span>
              </div>
            )}

            <div className="p-3 flex items-center justify-between">
              <span className="text-muted-foreground">SRS DOCUMENT</span>
              <span className="text-success">
                {srsFile ? `${srsFile.name} (${formatFileSize(srsFile.size)})` : 'None'}
              </span>
            </div>

            <div className="p-3 flex items-center justify-between">
              <span className="text-muted-foreground">ARCHITECTURE MODELS</span>
              <span className="text-foreground">
                {umlFiles.length > 0 ? `${umlFiles.length} file(s) attached` : 'None attached'}
              </span>
            </div>
          </div>

          <div className="pt-2 flex justify-between">
            <Button variant="outline" onClick={() => setCurrentStep(3)} disabled={loading}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Back
            </Button>
            <Button
              onClick={handleUploadAndAnalyze}
              loading={loading}
              disabled={loading}
              className="px-6"
            >
              Save draft and review extraction
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
