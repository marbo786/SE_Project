import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectsApi } from '@/lib/api'
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
  const [srsFile, setSrsFile] = useState<File | null>(null)

  // UML Diagrams
  const [umlFiles, setUmlFiles] = useState<{ type: string; file: File }[]>([])
  const [umlType, setUmlType] = useState('usecase')
  const [umlFile, setUmlFile] = useState<File | null>(null)

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false)

  // Status
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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

    setLoading(true)
    setError('')

    try {
      // 1. Create project
      const res = await projectsApi.create({ name, description })
      const projectId = res.data.id

      // 2. Upload SRS
      await projectsApi.uploadSRS(projectId, srsFile)

      // 3. Upload UML files sequentially
      for (const uml of umlFiles) {
        await projectsApi.uploadUML(projectId, uml.type, uml.file)
      }

      // 4. Trigger analysis
      await projectsApi.analyze(projectId)

      // 5. Navigate to report
      navigate(`/projects/${projectId}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Analysis pipeline initiation failed.')
      setLoading(false)
    }
  }

  const steps = [
    { num: 1, label: 'Scope & Metadata' },
    { num: 2, label: 'SRS Document' },
    { num: 3, label: 'Architecture UML' },
    { num: 4, label: 'Review & Ingest' },
  ]

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Navigation Breadcrumb */}
      <Breadcrumbs
        items={[
          { label: 'Specifications', href: '/projects' },
          { label: 'New Ingestion Pipeline' },
        ]}
      />

      <PageHeader
        title="Ingest Specification"
        description="Provide software requirement specification documents and architecture models for static evaluation."
      />

      {/* Step Navigation Bar */}
      <div className="flex border border-[#303136] rounded bg-[#17181B] text-xs font-mono overflow-hidden">
        {steps.map(step => {
          const active = currentStep === step.num
          const complete = currentStep > step.num
          return (
            <button
              key={step.num}
              onClick={() => setCurrentStep(step.num)}
              className={cn(
                "flex-1 py-2 px-3 text-left border-r border-[#303136] last:border-r-0 flex items-center gap-2 transition-none",
                active && "bg-[#1D1E22] text-[#E7E7E9] font-medium border-b-2 border-b-[#7895B5]",
                complete && "text-[#4E8752]",
                !active && !complete && "text-[#777981] hover:text-[#A1A1AA]"
              )}
            >
              <span className={cn(
                "w-4 h-4 rounded-sm flex items-center justify-center text-[10px]",
                active ? "bg-[#7895B5] text-[#111214] font-bold" : complete ? "bg-[#4E8752]/20 text-[#68A86C]" : "bg-[#24252A] text-[#777981]"
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
        <div className="p-3 rounded border border-[#C04848]/40 bg-[#C04848]/10 text-xs text-[#E06C6C] flex items-center gap-2 font-mono">
          <AlertCircle className="h-4 w-4 shrink-0 text-[#E06C6C]" />
          <span>{error}</span>
        </div>
      )}

      {/* STEP 1: Project Details */}
      {currentStep === 1 && (
        <div className="rounded border border-[#303136] bg-[#1D1E22] p-4 space-y-4">
          <div className="border-b border-[#303136] pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
              Step 1: Specification Scope & Identification
            </h3>
          </div>

          <div className="space-y-3">
            <div>
              <Label htmlFor="spec-name" className="text-xs text-[#E7E7E9] mb-1.5 block">
                Specification Name <span className="text-[#C04848]">*</span>
              </Label>
              <Input
                id="spec-name"
                placeholder="e.g. Flight Navigation System SRS"
                value={name}
                onChange={e => setName(e.target.value)}
                autoFocus
              />
              <p className="text-[11px] text-[#777981] mt-1">
                Unique identifier for tracking requirement versions over time.
              </p>
            </div>

            <div>
              <Label htmlFor="spec-desc" className="text-xs text-[#E7E7E9] mb-1.5 block">
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
        <div className="rounded border border-[#303136] bg-[#1D1E22] p-4 space-y-4">
          <div className="border-b border-[#303136] pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
              Step 2: Requirements Document Ingestion
            </h3>
          </div>

          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => srsInputRef.current?.click()}
            className={cn(
              "border border-dashed rounded p-6 text-center cursor-pointer transition-none",
              isDragging
                ? "border-[#7895B5] bg-[#7895B5]/10"
                : "border-[#303136] bg-[#17181B] hover:border-[#7895B5]/50 hover:bg-[#1D1E22]"
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
            <Upload className="h-6 w-6 mx-auto mb-2 text-[#7895B5]" />
            <p className="text-xs font-medium text-[#E7E7E9] mb-1">
              Select or drop specification document
            </p>
            <p className="text-[11px] font-mono text-[#777981]">
              Supported file formats: .PDF, .DOCX
            </p>
          </div>

          {/* Selected File Details */}
          {srsFile && (
            <div className="flex items-center justify-between p-2.5 rounded border border-[#303136] bg-[#17181B]">
              <div className="flex items-center gap-2 min-w-0">
                <FileText className="h-4 w-4 text-[#7895B5] shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-mono font-medium text-[#E7E7E9] truncate">{srsFile.name}</p>
                  <p className="text-[10px] font-mono text-[#777981]">{formatFileSize(srsFile.size)}</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-1.5 text-xs text-[#777981] hover:text-[#E06C6C]"
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
        <div className="rounded border border-[#303136] bg-[#1D1E22] p-4 space-y-4">
          <div className="border-b border-[#303136] pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
              Step 3: Architecture Diagram Models (Optional)
            </h3>
            <p className="text-[11px] text-[#777981] mt-0.5">
              Attach PlantUML diagram models (.puml, .txt) to generate requirement-to-architecture traceability matrices.
            </p>
          </div>

          <div className="p-3 rounded border border-[#303136] bg-[#17181B] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div>
                <Label className="text-[11px] text-[#777981] mb-1 block">Diagram Type</Label>
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
                <Label className="text-[11px] text-[#777981] mb-1 block">PlantUML Model File</Label>
                <div className="flex gap-2">
                  <input
                    ref={umlInputRef}
                    type="file"
                    accept=".txt,.puml"
                    className="text-xs text-[#E7E7E9] file:mr-2 file:py-1 file:px-2 file:rounded file:border file:border-[#303136] file:bg-[#1D1E22] file:text-[11px] file:text-[#E7E7E9] file:cursor-pointer flex-1"
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
              <p className="text-[11px] font-mono uppercase text-[#777981]">
                Attached Architecture Models ({umlFiles.length})
              </p>
              <div className="divide-y divide-[#303136] border border-[#303136] rounded bg-[#17181B] overflow-hidden">
                {umlFiles.map((item, idx) => (
                  <div key={idx} className="p-2 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0 font-mono">
                      <FileCode className="h-3.5 w-3.5 text-[#7895B5] shrink-0" />
                      <Badge variant="outline" className="text-[10px] uppercase">
                        {item.type}
                      </Badge>
                      <span className="text-[#E7E7E9] truncate">{item.file.name}</span>
                      <span className="text-[10px] text-[#777981]">({formatFileSize(item.file.size)})</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 px-1 text-[#777981] hover:text-[#E06C6C]"
                      onClick={() => setUmlFiles(umlFiles.filter((_, i) => i !== idx))}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-[#777981] italic">
              No architecture models attached. You may continue without UML models.
            </p>
          )}

          <div className="pt-2 flex justify-between">
            <Button variant="outline" onClick={() => setCurrentStep(2)}>
              <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
              Back
            </Button>
            <Button onClick={() => setCurrentStep(4)}>
              Review Ingestion Parameters
              <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 4: Review and Execute Ingestion */}
      {currentStep === 4 && (
        <div className="rounded border border-[#303136] bg-[#1D1E22] p-4 space-y-4">
          <div className="border-b border-[#303136] pb-2">
            <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-[#A1A1AA]">
              Step 4: Inspection Parameters Verification
            </h3>
          </div>

          <div className="divide-y divide-[#303136] border border-[#303136] rounded bg-[#17181B] text-xs font-mono">
            <div className="p-3 flex items-center justify-between">
              <span className="text-[#777981]">SPECIFICATION IDENTIFIER</span>
              <span className="text-[#E7E7E9] font-medium">{name}</span>
            </div>

            {description && (
              <div className="p-3 flex items-start justify-between">
                <span className="text-[#777981]">SCOPE / DESCRIPTION</span>
                <span className="text-[#E7E7E9] max-w-sm text-right font-sans text-xs">{description}</span>
              </div>
            )}

            <div className="p-3 flex items-center justify-between">
              <span className="text-[#777981]">SRS DOCUMENT</span>
              <span className="text-[#68A86C]">
                {srsFile ? `${srsFile.name} (${formatFileSize(srsFile.size)})` : 'None'}
              </span>
            </div>

            <div className="p-3 flex items-center justify-between">
              <span className="text-[#777981]">ARCHITECTURE MODELS</span>
              <span className="text-[#E7E7E9]">
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
              Execute Ingestion & Inspection
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
