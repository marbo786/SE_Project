import type { RevisionUpdate, RequirementUpdate } from '@/lib/generated-api'
import { useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiError, historyApi, projectsApi, Revision } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Requirement {
  internal_id: string; id: string | null; text: string; original_text: string; source_ref: string
  class: string; subtype: string | null
}
interface Extraction { requirements?: Requirement[]; warnings?: string[] }
const control = 'w-full rounded border border-border bg-secondary px-3 py-2 text-sm text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary'

function RequirementForm({ requirement, disabled, save }: { requirement: Requirement; disabled: boolean; save: (data: RequirementUpdate) => void }) {
  const [text, setText] = useState(requirement.text)
  const [identifier, setIdentifier] = useState(requirement.id || '')
  const [classification, setClassification] = useState(requirement.class)
  const [subtype, setSubtype] = useState(requirement.subtype || 'other')
  return <form onSubmit={event => { event.preventDefault(); save({ text, id: identifier || null, class: classification as RequirementUpdate['class'], subtype: subtype as RequirementUpdate['subtype'] }) }} className="py-6 space-y-3">
    <div className="flex flex-wrap justify-between gap-2"><h3 className="font-semibold">{requirement.id || 'Requirement without an ID'}</h3><p className="text-sm text-muted-foreground">{requirement.source_ref}</p></div>
    <label className="block text-sm space-y-2"><span>Requirement text</span><textarea required maxLength={20000} rows={3} className={control} value={text} onChange={event => setText(event.target.value)} disabled={disabled} /></label>
    <div className="grid sm:grid-cols-3 gap-3">
      <label className="text-sm space-y-2"><span>Authored ID</span><input maxLength={128} className={control} value={identifier} onChange={event => setIdentifier(event.target.value)} disabled={disabled} /></label>
      <label className="text-sm space-y-2"><span>Classification</span><select className={control} value={classification} onChange={event => setClassification(event.target.value)} disabled={disabled}><option value="functional">Functional</option><option value="non_functional">Non-functional</option></select></label>
      <label className="text-sm space-y-2"><span>Quality category</span><select className={control} value={subtype} onChange={event => setSubtype(event.target.value)} disabled={disabled}>{['other', 'performance', 'availability', 'security', 'usability', 'reliability', 'maintainability', 'portability'].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
    </div>
    <div className="flex flex-wrap items-start justify-between gap-3">
      <details className="text-sm max-w-prose text-muted-foreground"><summary className="cursor-pointer focus-visible:outline">Original extracted text</summary><p className="mt-2 whitespace-pre-wrap">{requirement.original_text}</p></details>
      <Button type="button" variant="outline" disabled={disabled || text === requirement.original_text} onClick={() => { setText(requirement.original_text); save({ text: requirement.original_text }) }}>Restore original text</Button>
      <Button type="submit" variant="outline" disabled={disabled || !text.trim()}>Save requirement</Button>
    </div>
  </form>
}

export default function DraftPage() {
  const { id, revisionId } = useParams()
  const pid = Number(id), rid = Number(revisionId)
  const navigate = useNavigate(), cache = useQueryClient()
  const [notice, setNotice] = useState(''), [error, setError] = useState('')
  const [kind, setKind] = useState('srs'), [file, setFile] = useState<File | null>(null), [replace, setReplace] = useState('')
  const [uploadProgress, setUploadProgress] = useState<number | null>(null)
  const [confirmed, setConfirmed] = useState<boolean | null>(null)
  const keys = useRef(new Map<string, string>())
  const keyFor = (operation: string) => { if (!keys.current.has(operation)) keys.current.set(operation, crypto.randomUUID()); return keys.current.get(operation)! }
  const query = useQuery({ queryKey: ['draft', pid, rid], queryFn: async () => {
    const [project, revision, extraction] = await Promise.all([projectsApi.get(pid), historyApi.revision(pid, rid), historyApi.extraction(pid, rid)])
    return { project: project.data, revision: revision.data, canonical: extraction.data.canonical as { artifacts: Record<string, Extraction> } | null }
  }, enabled: Number.isInteger(pid) && Number.isInteger(rid) })
  const command = useMutation({ mutationFn: (work: () => Promise<unknown>) => work(),
    onSuccess: async () => { setUploadProgress(null); setError(''); setNotice('Changes saved.'); await cache.invalidateQueries({ queryKey: ['draft', pid, rid] }); await cache.invalidateQueries({ queryKey: ['project-report', pid] }) },
    onError: value => { setUploadProgress(null); setNotice(''); setError(apiError(value)); },
  })
  const revision = query.data?.revision
  const act = (work: (revision: Revision) => Promise<unknown>) => { if (revision) { setNotice(''); setError(''); command.mutate(() => work(revision)) } }
  const editOptions = (data: RevisionUpdate) => act(async value => {
    try {
      const result = await historyApi.edit(pid, value, data)
      cache.setQueryData(['draft', pid, rid], (previous: typeof query.data) => previous ? { ...previous, revision: result.data } : previous)
    } finally { setConfirmed(null) }
  })
  if (query.isPending) return <p role="status">Loading your draft…</p>
  if (query.isError || !revision) return <div role="alert"><p>{apiError(query.error, 'This draft could not be loaded.')}</p><Button onClick={() => query.refetch()}>Try again</Button></div>
  const readOnly = revision.state !== 'draft', busy = command.isPending || readOnly
  return <div className="max-w-5xl mx-auto space-y-6 pb-12">
    <Link to={`/projects/${pid}`} className="text-sm underline text-primary">Back to report and history</Link>
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
      <div><h1 className="text-2xl font-semibold">{query.data?.project.name}</h1><p className="text-muted-foreground mt-2">Revision {revision.number} {readOnly ? 'is sealed' : 'draft'}</p></div>
      <Button disabled={busy || !revision.extraction_confirmed} onClick={() => act(async value => {
        const run = await historyApi.start(pid, value, keyFor(`run:${value.edit_version}`)); navigate(`/projects/${pid}?run=${run.data.id}`)
      })}>{command.isPending ? 'Saving…' : 'Analyze this revision'}</Button>
    </header>
    {readOnly && <p className="p-4 border rounded">This revision has been analyzed. Create a draft from the report to make further changes.</p>}
    {notice && <p role="status" className="text-success">{notice}</p>}
    {error && <div role="alert" className="border border-red-300 rounded p-4 space-y-2"><p>{error}</p><Button variant="outline" onClick={() => query.refetch()}>Refresh draft</Button></div>}
    <section aria-labelledby="scope-heading" className="space-y-3">
      <h2 id="scope-heading" className="text-lg font-semibold">Analysis scope</h2>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="text-sm space-y-2"><span>Profile</span><select className={control} disabled={busy} value={revision.analysis_profile} onChange={event => editOptions({ analysis_profile: event.currentTarget.value as RevisionUpdate['analysis_profile'] })}><option value="srs_only">Requirements only</option><option value="architecture">Requirements and architecture</option></select></label>
        <label className="text-sm space-y-2"><span>Checks</span><select className={control} disabled={busy} value={revision.analysis_mode} onChange={event => editOptions({ analysis_mode: event.currentTarget.value as RevisionUpdate['analysis_mode'] })}><option value="deterministic">Deterministic checks</option><option value="ai">Deterministic and AI checks</option></select></label>
      </div>
    </section>
    <section aria-labelledby="files-heading" className="space-y-4 rounded border border-border p-5 bg-card">
      <h2 id="files-heading" className="text-lg font-semibold">Source documents</h2>
      <p className="text-sm text-muted-foreground max-w-prose">Add one SRS and up to 19 diagrams. Replacing a source clears extraction corrections in this draft. Earlier revisions keep their files and reports.</p>
      <ul className="divide-y divide-border">{revision.artifacts.map(artifact => <li key={artifact.id} className="py-3 flex items-center justify-between gap-3">
        <div className="min-w-0"><a className="underline break-all text-primary" href={historyApi.source(pid, artifact.id)}>{artifact.filename}</a><p className="text-sm text-muted-foreground">{artifact.type.replace('uml_', '')}</p></div>
        <Button variant="outline" disabled={busy} onClick={() => act(value => historyApi.remove(pid, value, artifact.id))}>Remove</Button>
      </li>)}</ul>
      {!revision.artifacts.length && <p className="text-sm text-muted-foreground">Add an SRS document to begin.</p>}
      {uploadProgress !== null && <div role="status"><progress aria-label="Source upload" max={100} value={uploadProgress} /> {uploadProgress === 100 ? 'Upload sent. Validating source…' : `Uploading ${uploadProgress}%`}</div>}
      <form className="grid sm:grid-cols-2 gap-3" onSubmit={event => { event.preventDefault(); if (file && file.size > 10 * 1024 * 1024) { setError('Choose a file smaller than 10 MB.'); return } if (file) { setUploadProgress(0); act(value => historyApi.upload(pid, value, kind, file, keyFor(`upload:${value.edit_version}:${kind}:${replace}:${file.name}:${file.size}:${file.lastModified}`), replace ? Number(replace) : undefined, setUploadProgress)) } }}>
        <label className="text-sm space-y-2"><span>Document type</span><select className={control} value={kind} disabled={busy} onChange={event => { setKind(event.target.value); setReplace('') }}><option value="srs">SRS document</option><option value="uml_usecase">Use-case diagram</option><option value="uml_class">Class diagram</option><option value="uml_sequence">Sequence diagram</option></select></label>
        <label className="text-sm space-y-2"><span>Add or replace</span><select className={control} value={replace} disabled={busy} onChange={event => setReplace(event.target.value)}><option value="">Add a new file</option>{revision.artifacts.filter(a => a.type === kind).map(a => <option value={a.id} key={a.id}>Replace {a.filename}</option>)}</select></label>
        <label className="text-sm space-y-2"><span>{kind === 'srs' ? 'DOCX or text-based PDF, up to 10 MB' : 'PlantUML text, up to 10 MB'}</span><input type="file" required className={control} disabled={busy} accept={kind === 'srs' ? '.docx,.pdf' : '.puml,.plantuml,.txt'} onChange={event => setFile(event.target.files?.[0] || null)} /></label>
        <div className="self-end"><Button type="submit" disabled={busy || !file}>Save source file</Button></div>
      </form>
    </section>
    <section aria-labelledby="extraction-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3"><h2 id="extraction-heading" className="text-lg font-semibold">Review extracted requirements</h2>{!query.data?.canonical && <Button disabled={busy || !revision.artifacts.some(a => a.type === 'srs')} onClick={() => act(value => historyApi.extract(pid, value))}>Extract requirements</Button>}</div>
      <p className="text-sm text-muted-foreground max-w-prose">Check the text, IDs, and classification against the source. Saved corrections apply to this revision; the original file remains available.</p>
      {query.data?.canonical && <p>{Object.values(query.data.canonical.artifacts).reduce((count, extraction) => count + (extraction.requirements?.length || 0), 0)} requirements extracted from {revision.artifacts.length} sources.</p>}
      {query.data?.canonical ? <div className="divide-y divide-border">{Object.entries(query.data.canonical.artifacts).map(([aid, extraction]) => <div key={aid}>
        {(extraction.warnings || []).map((warning, index) => <p key={index} className="py-2 text-amber-200">{warning}</p>)}
        {(extraction.requirements || []).map(requirement => <RequirementForm key={`${requirement.internal_id}:${requirement.text}:${requirement.id}:${requirement.class}:${requirement.subtype}`} requirement={requirement} disabled={busy} save={data => act(value => historyApi.correct(pid, value, requirement.internal_id, data))} />)}
      </div>)}</div> : <p className="py-6 text-muted-foreground">Extract the uploaded files to review their contents before analysis.</p>}
      {query.data?.canonical && <label className="flex gap-3 items-start border-t border-border pt-5"><input type="checkbox" className="mt-1 h-4 w-4" disabled={busy} checked={confirmed ?? revision.extraction_confirmed} onChange={event => { const checked = event.currentTarget.checked; setConfirmed(checked); editOptions({ extraction_confirmed: checked }) }} /><span>I have reviewed the extracted content and am ready to analyze this revision.</span></label>}
    </section>
  </div>
}
